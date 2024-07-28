#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import copy
import datetime
import json
import math
import os
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

import _hkml
import hkml_cache
import hkml_fetch
import hkml_open
import hkml_tag
import hkml_thread
import hkml_view

class MailsList:
    txt = None
    mail_idx_to_mail_cache_key = None
    date = None

    def __init__(self, txt, mail_idx_to_cache_key, date):
        self.txt = txt
        self.map_idx_to_mail_cache_key = mail_idx_to_cache_key
        self.date = date
        if self.date is None:
            self.date = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    def to_kvpairs(self):
        return {
                'output': self.txt,
                'index_to_cache_key': self.mail_idx_to_mail_cache_key,
                'date': self.date
                }

    @classmethod
    def from_kvpairs(cls, kvpairs):
        self = cls(kvpairs['output'], kvpairs['index_to_cache_key'],
                   kvpairs['date'])

'''
Contains list command generated outputs to cache for later fast processing.
Keys are the json string of the list command arguments, or 'thread_output'.
Values are a dict containing below key/values.
- 'output': the list command's terminal output string.
- 'index_to_cache_key': a dict having the mail index on the output as keys, and
  the corresponding mail's key in the mail cache as values.
- 'date': last accessed date
'''
mails_lists_cache = None

def list_output_cache_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'list_output_cache')

def args_to_lists_cache_key(args):
    dict_ = copy.deepcopy(args.__dict__)
    dict_['fetch'] = False
    dict_['stdout'] = False

    return json.dumps(dict_, sort_keys=True)

def get_mails_lists_cache():
    global mails_lists_cache

    if mails_lists_cache is None:
        if not os.path.isfile(list_output_cache_file_path()):
            mails_lists_cache = {}
        else:
            with open(list_output_cache_file_path(), 'r') as f:
                mails_lists_cache = json.load(f)
    if mails_lists_cache is None:
        mails_lists_cache = {}
    return mails_lists_cache

def writeback_list_output():
    cache = get_mails_lists_cache()
    with open(list_output_cache_file_path(), 'w') as f:
        json.dump(cache, f, indent=4)

def get_cached_list_outputs(key):
    cache = get_mails_lists_cache()
    if not key in cache:
        return None
    outputs = cache[key]
    outputs['date'] = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    return outputs

def get_list_for(key):
    outputs = get_cached_list_outputs(key)
    if outputs is None:
        return None, None
    return outputs['output'], outputs['index_to_cache_key']

def get_last_mails_list():
    cache = get_mails_lists_cache()
    keys = [k for k in cache]
    key = sorted(keys, key=lambda x: cache[x]['date'])[-1]
    outputs = get_cached_list_outputs(key)
    if outputs is None:
        return None, None
    return outputs['output'], outputs['index_to_cache_key']

def get_last_list():
    cache = get_mails_lists_cache()
    keys = [k for k in cache if k != 'thread_output']
    key = sorted(keys, key=lambda x: cache[x]['date'])[-1]
    outputs = get_cached_list_outputs(key)
    if outputs is None:
        return None
    return outputs['output'], outputs['index_to_cache_key']

def get_last_thread():
    cache = get_mails_lists_cache()
    outputs = get_cached_list_outputs('thread_output')
    if outputs is None:
        return None
    return outputs['output'], outputs['index_to_cache_key']

def invalidate_cached_outputs(source):
    keys_to_del = []
    cache = get_mails_lists_cache()
    for key in cache.keys():
        try:
            key_dict = json.loads(key)
            if key_dict['source'] == source:
                keys_to_del.append(key)
        except:
            pass
    for key in keys_to_del:
        del cache[key]

def writeback_list_output_cache():
    cache = get_mails_lists_cache()
    with open(list_output_cache_file_path(), 'w') as f:
        json.dump(cache, f, indent=4)

def cache_list_str(key, list_str, mail_idx_key_map):
    cache = get_mails_lists_cache()
    cache[key] = {
            'output': '\n'.join(['# (cached output)', list_str]),
            'index_to_cache_key': mail_idx_key_map,
            'date': datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}
    max_cache_sz = 64
    if len(cache) == max_cache_sz:
        keys = sorted(cache.keys(), key=lambda x: cache[x]['date'])
        del cache[keys[0]]
    writeback_list_output_cache()

def get_mail(idx, not_thread_idx=False):
    cache = get_mails_lists_cache()
    sorted_keys = sorted(cache.keys(), key=lambda x: cache[x]['date'])
    if not_thread_idx and sorted_keys[-1] == 'thread_output':
        last_key = sorted_keys[-2]
    else:
        last_key = sorted_keys[-1]
    idx_to_keys = cache[last_key]['index_to_cache_key']
    idx_str = '%d' % idx
    if not idx_str in idx_to_keys:
        return None

    output_string_lines = cache[last_key]['output'].split('\n')
    if output_string_lines[0].startswith('# last reference: '):
        output_string_lines = output_string_lines[2:]
    output_string_lines = ['# last reference: %d' % idx,
                           '#'] + output_string_lines
    cache[last_key]['output'] = '\n'.join(output_string_lines)
    writeback_list_output()

    mail_key = idx_to_keys[idx_str]
    return hkml_cache.get_mail(key=mail_key)

def map_idx_to_mail_cache_key(mail, mail_idx_key_map):
    idx = mail.pridx
    key = hkml_cache.get_cache_key(
            mail.gitid, mail.gitdir, mail.get_field('message-id'))

    idx_str = '%d' % idx
    if idx_str in mail_idx_key_map:
        return
    mail_idx_key_map[idx_str] = key

class MailListDecorator:
    collapse = None
    sort_threads_by = None
    ascend = None
    cols = None
    show_url = None
    hide_stat = None
    runtime_profile = None
    max_len = None

    def __init__(self, args):
        if args is None:
            return

        self.collapse = args.collapse
        self.sort_threads_by = args.sort_threads_by
        self.ascend = args.ascend
        self.cols = args.cols
        self.show_url = args.url
        self.hide_stat = args.hide_stat
        self.runtime_profile = args.runtime_profile
        self.max_len = args.max_len_list

        if args.hot:
            self.ascend = False
            self.sort_threads_by = ['last_date', 'nr_comments']
            self.collapse = True

    def to_kvpairs(self):
        kvpairs = copy.deepcopy(vars(self))
        return {k: v for k, v in kvpairs.items() if v is not None}

    @classmethod
    def from_kvpairs(cls, kvpairs):
        self = cls(None)
        for key, value in kvpairs.items():
            setattr(self, key, value)
        return self

def wrap_line(prefix, line, nr_cols):
    '''Wrap a string for a limited columns and returns a list of resulting
    lines.  Second and below lines starts with spaces of 'prefix' length.
    For example:
    >>> print('\n'.join(hkml_list.wrap_line('[something]', 'foo bar baz asdf', 20)))
    [something] foo bar
                baz asdf
    '''
    lines = []
    words = [prefix] + line.split(' ')
    words_to_print = []
    for w in words:
        words_to_print.append(w)
        line_len = len(' '.join(words_to_print))
        if nr_cols is not None and line_len > nr_cols:
            if len(words_to_print) == 1:
                lines.append(words_to_print[0])
            else:
                lines.append(' '.join(words_to_print[:-1]))
                words_to_print = [' ' * (len(prefix) + 1) + words_to_print[-1]]
    lines.append(' '.join(words_to_print))
    return lines

def threads_of(mails):
    by_msgids = {}
    for mail in mails:
        by_msgids[mail.get_field('message-id')] = mail

    threads = []
    for mail in mails:
        in_reply_to = mail.get_field('in-reply-to')
        if not in_reply_to in by_msgids:
            threads.append(mail)
        else:
            orig_mail = by_msgids[in_reply_to]
            orig_mail.replies.append(mail)
            mail.parent_mail = orig_mail
    return threads

def orig_subject_formatted(mail):
    if mail.parent_mail is None:
        return False
    if mail.parent_mail.filtered_out == False:
        return True
    return orig_subject_formatted(mail.parent_mail)

def format_entry(mail, max_digits_for_idx, show_nr_replies, show_url, nr_cols):
    index = '%d' % mail.pridx
    nr_zeroes = max_digits_for_idx - len(index)
    index = '%s%s' % ('0' * nr_zeroes, index)
    prefix = '[%s]%s' % (index, ' ' * 2 * mail.prdepth)

    subject = '%s' % mail.get_field('subject')
    if mail.prdepth and subject.lower().startswith('re: '):
        subject = subject[4:]
        if orig_subject_formatted(mail):
            parent_subject = mail.parent_mail.get_field('subject')
            if parent_subject[:4].lower() == 're: ':
                parent_subject = parent_subject[4:]
            if parent_subject == subject:
                subject = 're:'

    from_fields = mail.get_field('from').split()
    if len(from_fields) > 1:
        from_fields = from_fields[0:-1]
    suffices = [' '.join(from_fields), mail.date.strftime('%Y/%m/%d %H:%M')]
    if show_nr_replies:
        suffices.append('%d+ msgs' % nr_replies_of(mail))
    if show_url:
        suffices.append(mail.url())
    suffix = ' (%s)' % ', '.join(suffices)

    lines = wrap_line(prefix, subject + suffix, nr_cols)
    return lines

def nr_replies_of(mail):
    nr = len(mail.replies)
    for re in mail.replies:
        nr += nr_replies_of(re)
    return nr

def root_of_thread(mail):
    if mail.parent_mail is None:
        return mail
    return root_of_thread(mail.parent_mail)

def set_index(mail, list_, depth, mail_idx_key_map):
    """ Make mails to be all ready for print in list"""
    mail.pridx = len(list_)
    mail.prdepth = depth
    list_.append(mail)

    map_idx_to_mail_cache_key(mail, mail_idx_key_map)

    for mail in mail.replies:
        set_index(mail, list_, depth + 1, mail_idx_key_map)

def last_reply_date(mail, prev_last_date):
    if len(mail.replies) == 0:
        if prev_last_date == None or prev_last_date < mail.date:
            return mail.date
        return prev_last_date

    for reply in mail.replies:
        prev_last_date = last_reply_date(reply, prev_last_date)
    return prev_last_date

def nr_comments(mail):
    nr_comments = nr_replies_of(mail)
    # Exclude replies that sent together as a patch series
    if not mail.get_field('in-reply-to') and mail.series is not None:
        nr_comments -= mail.series[1]
    return nr_comments

def sort_threads(threads, category):
    if category == 'first_date':
        return
    if category == 'last_date':
        threads.sort(key=lambda t: last_reply_date(t, None))
    elif category == 'nr_replies':
        threads.sort(key=lambda t: nr_replies_of(t))
    elif category == 'nr_comments':
        threads.sort(key=lambda t: nr_comments(t))

def keywords_in(keywords, text):
    if keywords is None:
        return True
    for keyword in keywords:
        if keyword is not None and not keyword in text:
            return False
    return True

class MailListFilter:
    new_threads_only = None
    from_keywords = None
    from_to_keywords = None
    from_to_cc_keywords = None
    subject_keywords = None
    body_keywords = None

    def __init__(self, args):
        if args is None:
            return
        self.new_threads_only = args.new
        self.from_keywords = args.from_keywords
        self.from_to_keywords = args.from_to_keywords
        self.from_to_cc_keywords = args.from_to_cc_keywords
        self.subject_keywords = args.subject_keywords
        self.body_keywords = args.body_keywords

    def no_filter_set(self):
        return (not self.new_threads_only and not self.from_keywords and
            not self.from_to_keywords and not self.from_to_cc_keywords and
            not self.subject_keywords and not self.body_keywords)

    def should_filter_out(self, mail):
        if self.no_filter_set():
            return False

        if self.new_threads_only and mail.get_field('in-reply-to'):
            return True
        if not keywords_in(self.from_keywords, mail.get_field('from')):
            return True
        if not keywords_in(
                self.from_to_keywords,
                '%s %s' % (mail.get_field('from'), mail.get_field('to'))):
            return True
        if not keywords_in(
                self.from_to_cc_keywords,
                '%s %s %s' % (mail.get_field('from'), mail.get_field('to'),
                              mail.get_field('cc'))):
            return True
        if not keywords_in(self.subject_keywords, mail.subject):
            return True
        if not keywords_in(self.body_keywords, mail.get_field('body')):
            return True

        return False

    def to_kvpairs(self):
        kvpairs = copy.deepcopy(vars(self))
        return {k: v for k, v in kvpairs.items() if v is not None}

    @classmethod
    def from_kvpairs(cls, kvpairs):
        self = cls(None)
        for key, value in kvpairs.items():
            setattr(self, key, value)
        return self

def should_filter_out(mail, ls_range, new_threads_only,
                      from_keywords, from_to_keywords,
                      from_to_cc_keywords, subject_keywords, body_keywords):
    if ls_range is not None and not mail.pridx:
        return True
    if new_threads_only and mail.get_field('in-reply-to'):
        return True
    if not keywords_in(from_keywords, mail.get_field('from')):
        return True
    if not keywords_in(
            from_to_keywords,
            '%s %s' % (mail.get_field('from'), mail.get_field('to'))):
        return True
    if not keywords_in(
            from_to_cc_keywords,
            '%s %s %s' % (mail.get_field('from'), mail.get_field('to'),
                          mail.get_field('cc'))):
        return True
    if not keywords_in(subject_keywords, mail.subject):
        return True
    if not keywords_in(body_keywords, mail.get_field('body')):
        return True

    return False

def format_stat(mails_to_show, stat_authors):
    nr_threads = 0
    nr_new_threads = 0
    nr_patches = 0
    nr_patchsets = 0
    oldest = None
    latest = None
    authors_nr_mails = {}
    for mail in mails_to_show:
        if mail.parent_mail is None:
            nr_threads += 1
        if not mail.get_field('in-reply-to'):
            nr_new_threads += 1
        if 'patch' in mail.subject_tags:
            nr_patches += 1
        if 'patch' in mail.subject_tags and not mail.get_field('in-reply-to'):
            nr_patchsets += 1
        if oldest is None or mail.date < oldest.date:
            oldest = mail
        if latest is None or latest.date < mail.date:
            latest = mail
        author = mail.get_field('from')
        if not author in authors_nr_mails:
            authors_nr_mails[author] = 0
        authors_nr_mails[author] += 1

    lines = []
    lines.append('# %d mails, %d threads, %d new threads' %
            (len(mails_to_show), nr_threads, nr_new_threads))
    lines.append('# %d patches, %d series' % (nr_patches, nr_patchsets))
    if oldest is not None:
        lines.append('# oldest: %s' % oldest.date)
        lines.append('# newest: %s' % latest.date)
    if stat_authors:
        authors = [[x, authors_nr_mails[x]]
                   for x in sorted(authors_nr_mails.keys(), reverse=True,
                                   key=lambda x: authors_nr_mails[x])[:10]]
        lines.append('# top %d authors' % len(authors))
        for author, nr_mails in authors:
            lines.append('# - %s: %d' % (author, nr_mails))
    return lines

def sort_filter_mails(mails_to_show, mails_filter, list_decorator,
                      show_thread_of, runtime_profile):

    timestamp = time.time()
    threads = threads_of(mails_to_show)
    sort_threads_by = list_decorator.sort_threads_by
    for sort_category in sort_threads_by:
        sort_threads(threads, sort_category)
    descend = not list_decorator.ascend
    if descend:
        threads.reverse()
    runtime_profile.append(['threads_extract', time.time() - timestamp])

    by_pr_idx = []
    timestamp = time.time()
    mail_idx_key_map = {}
    for mail in threads:
        set_index(mail, by_pr_idx, 0, mail_idx_key_map)
    runtime_profile.append(['set_index', time.time() - timestamp])

    timestamp = time.time()
    # Show all by default
    if show_thread_of is None:
        start_idx = 0
        end_idx = list_decorator.max_len
        if end_idx is None:
            end_idx = len(mails_to_show)
    else:
        mail = by_pr_idx[show_thread_of]
        root = root_of_thread(mail)
        start_idx = root.pridx
        end_idx = root.pridx + nr_replies_of(root) + 1
    ls_range = range(start_idx, end_idx)

    filtered_mails = []
    for mail in by_pr_idx:
        if ls_range is not None and not mail.pridx in ls_range:
            mail.filtered_out = True
            continue
        if mails_filter is not None and mails_filter.should_filter_out(mail):
            mail.filtered_out = True
            continue
        mail.filtered_out = False
        filtered_mails.append(mail)
    runtime_profile.append(['filtering', time.time() - timestamp])
    return filtered_mails, mail_idx_key_map

def child_of_collapsed(mail, mails_to_collapse):
    if mail.parent_mail is None:
        return False
    if mail.parent_mail.pridx in mails_to_collapse:
        return True
    return child_of_collapsed(mail.parent_mail, mails_to_collapse)

def fmt_mails_text(mails, list_decorator, mails_to_collapse):
    lines = []
    collapse_threads = list_decorator.collapse
    show_url = list_decorator.show_url
    nr_cols = list_decorator.cols

    max_index = mails[-1].pridx
    if max_index == 0:
        max_index = 1
    max_digits_for_idx = math.ceil(math.log(max_index, 10))

    if mails_to_collapse:
        # set parent_mail
        threads_of(mails)

    for mail in mails:
        show_nr_replies = False
        if collapse_threads == True:
            if mail.prdepth > 0:
                continue
            show_nr_replies = True
        if mail.pridx in mails_to_collapse:
            show_nr_replies = True
        if child_of_collapsed(mail, mails_to_collapse):
            continue
        lines += format_entry(mail, max_digits_for_idx, show_nr_replies,
                              show_url, nr_cols)
    return lines

def mails_to_str(mails_to_show, mails_filter, list_decorator, show_thread_of,
                 runtime_profile, stat_only, stat_authors):
    if len(mails_to_show) == 0:
        return 'no mail', {}

    filtered_mails, mail_idx_key_map = sort_filter_mails(
            mails_to_show, mails_filter, list_decorator, show_thread_of,
            runtime_profile)

    timestamp = time.time()

    lines = fmt_mails_text(filtered_mails, list_decorator,
                           mails_to_collapse={})

    stat_lines = []
    show_stat = not list_decorator.hide_stat
    if show_stat:
        total_stat_lines = format_stat(mails_to_show, stat_authors)
        filtered_stat_lines = format_stat(filtered_mails, stat_authors)
        if total_stat_lines == filtered_stat_lines:
            stat_lines += total_stat_lines
        else:
            stat_lines.append('# stat for total mails')
            stat_lines += total_stat_lines
            stat_lines.append('#')
            stat_lines.append('# stat for filtered mails')
            stat_lines += filtered_stat_lines

    runtime_profile_lines = []
    total_profiled_time = sum([profile[1] for profile in runtime_profile])
    show_runtime_profile = list_decorator.runtime_profile
    if show_runtime_profile is True or total_profiled_time > 3:
        runtime_profile.append(['etc', time.time() - timestamp])
        runtime_profile_lines = ['# runtime profile']
        for key, value in runtime_profile:
            runtime_profile_lines.append('# %s: %s' % (key, value))
        runtime_profile_lines.append('#')

    if stat_only:
        return '\n'.join(stat_lines), mail_idx_key_map
    lines = runtime_profile_lines + stat_lines + lines
    return '\n'.join(lines), mail_idx_key_map

def git_log_output_line_to_mail(line, mdir):
    fields = line.split()
    if len(fields) < 3:
        return None
    subject_offset = len(fields[0]) + 1 + len(fields[1]) + 1
    subject = line[subject_offset:]
    return _hkml.Mail.from_gitlog(fields[0], mdir, fields[1], subject)

def get_mails_from_git(mail_list, since, until,
                       min_nr_mails, max_nr_mails, commits_range=None):
    lines = []
    mdirs = _hkml.mail_list_data_paths(mail_list)
    if not mdirs:
        print("Mailing list '%s' in manifest not found." % mail_list)
        exit(1)

    mails = []
    for mdir in mdirs:
        lines = []
        if not os.path.isdir(mdir):
            break
        base_cmd = ['git', '--git-dir=%s' % mdir, 'log',
                '--date=iso-strict', '--pretty=%H %ad %s']
        if commits_range is not None:
            base_cmd += [commits_range]

        cmd = base_cmd + []

        if since is not None:
            cmd += ['--since=%s' % since]
        if until:
            cmd += ['--until=%s' % until]
        if max_nr_mails is not None:
            cmd += ['-n', max_nr_mails]
        try:
            lines = _hkml.cmd_lines_output(cmd)
        except:
            # maybe commits_range is given, but the commit is not in this mdir
            pass

        if min_nr_mails is not None and len(lines) < min_nr_mails:
            cmd = base_cmd + ['-n', '%d' % min_nr_mails]
            if until:
                cmd += ['--until=%s' % until]
            try:
                lines = _hkml.cmd_lines_output(cmd)
            except:
                # maybe commits_range is given, but the commit is not in this
                # mdir
                pass

        for line in lines:
            mail = git_log_output_line_to_mail(line, mdir)
            # mbox can be empty string if the commit is invalid one.
            if mail is None or mail.mbox == '':
                continue
            mails.append(mail)
    return mails

def infer_source_type(source, is_pisearch):
    '''Return source type and error string'''
    candidates = []

    if source == 'clipboard':
        candidates.append('clipboard')
    if os.path.isfile(source):
        candidates.append('mbox')
    if hkml_tag.tag_exists(source):
        candidates.append('tag')
    if _hkml.is_valid_mail_list(source):
        candidates.append('mailing_list')
    elif source == 'all' and is_pisearch is True:
        candidates.append('mailing_list')
    if '@' in source:
        candidates.append('msgid')

    if len(candidates) == 0:
        return None, 'no candidate'
    elif len(candidates) > 1:
        return None, 'multiple candidates (%s)' % ', '.join(candidates)
    return candidates[0], None

def pisearch_tag(node):
    prefix='{http://www.w3.org/2005/Atom}'
    if not node.tag.startswith(prefix):
        return ''
    return node.tag[len(prefix):]

def get_mails_from_pisearch(mailing_list, query_str):
    '''Get mails from public inbox search query'''
    pi_url = _hkml.get_manifest()['site']
    query_str = query_str.replace(' ', '+')
    query_url = '%s/%s/?q=%s&x=A' % (pi_url, mailing_list, query_str)
    _, query_output = tempfile.mkstemp(prefix='hkml_pisearch_atom-')
    if subprocess.call(['curl', query_url, '-o', query_output],
                       stderr=subprocess.DEVNULL) != 0:
        print('fetching query result from %s failed' % query_url)
        return []
    try:
        root = ET.parse(query_output).getroot()
    except:
        print('parsing query result of %s at %s failed' %
              (query_url, query_output))
        return []
    os.remove(query_output)
    entries = [node for node in root if pisearch_tag(node) == 'entry']
    mails = []
    for entry in entries:
        mails.append(_hkml.Mail(atom_entry=entry, atom_ml=mailing_list))
    return mails

def get_mails(source, fetch, since, until,
              min_nr_mails, max_nr_mails, commits_range=None,
              source_type=None, pisearch=None):
    if source_type is None:
        source_type, err = infer_source_type(source, pisearch is not None)
        if err is not None:
            print('source type inference for %s failed: %s' % (source, err))
            print('you could use --source_type option to solve this')
            exit(1)

    if source_type == 'clipboard':
        mails, err = _hkml.read_mails_from_clipboard()
        if err != None:
            print('reading mails from clipboard failed: %s' % err)
            exit(1)
        if max_nr_mails is not None:
            mails = mails[:max_nr_mails]
        mails.sort(key=lambda mail: mail.date)
        return mails

    if source_type == 'mbox':
        mails = _hkml.read_mbox_file(source)
        if max_nr_mails is not None:
            mails = mails[:max_nr_mails]
        mails.sort(key=lambda mail: mail.date)
        return mails

    if source_type == 'tag':
        return hkml_tag.mails_of_tag(source)

    if pisearch:
        return get_mails_from_pisearch(source, pisearch)

    if source_type == 'msgid':
        mails, err = hkml_thread.get_thread_mails_from_web(source)
        if err is not None:
            print('getting mails for msgid %s failed' % source)
            exit(1)
        return mails

    if fetch:
        hkml_fetch.fetch_mail([source], True, 1)

    mails = get_mails_from_git(source, since, until, min_nr_mails,
                               max_nr_mails, commits_range)
    mails.reverse()
    return mails

def last_listed_mails():
    cache = get_mails_lists_cache()
    last_key = sorted(cache.keys(), key=lambda x: cache[x]['date'])[-1]
    idx_to_keys = cache[last_key]['index_to_cache_key']
    mails = []
    for idx in sorted([int(idx) for idx in idx_to_keys.keys()]):
        cache_key = idx_to_keys['%d' % idx]
        mail = hkml_cache.get_mail(key=cache_key)
        if mail is not None:
            mail.pridx = int(idx)
            mails.append(mail)
    return mails

def show_list(text, to_stdout, to_less, mail_idx_key_map):
    if to_stdout:
        print(text)
    if to_less:
        hkml_open.pr_with_pager_if_needed(text)
    hkml_view.view_mails_list(text, mail_idx_key_map)

def main(args):
    if args.source_type is not None:
        if len(args.source_type) == 1:
            args.source_type = args.source_type * len(args.sources)
        else:
            print('numbers of --source_type and --sources mismatch')
            exit(1)
    else:
        args.source_type = []
        for source in args.sources:
            source_type, err = infer_source_type(
                    source, args.pisearch is not None)
            if err is not None:
                print('source type inference for %s failed: %s' %
                      (source, err))
                print('you could use --source_type option to solve this')
                exit(1)
            args.source_type.append(source_type)

    lists_cache_key = args_to_lists_cache_key(args)
    use_cached_output = True
    for source_type in args.source_type:
        if source_type != 'mailing_list':
            use_cached_output = False
            break
    if args.ignore_cache is True:
        use_cached_output = False
    if use_cached_output and (args.fetch == False or args.sources == []):
        if args.sources == []:
            to_show, mail_idx_key_map = get_last_list()
            if to_show is None:
                print('no valid last list output exists')
                exit(1)
        else:
            to_show, mail_idx_key_map = get_list_for(lists_cache_key)
        if to_show is not None:
            writeback_list_output()
            show_list(to_show, args.stdout, args.use_less, mail_idx_key_map)
            return
    else:
        for source in args.sources:
            invalidate_cached_outputs(source)

    if args.nr_mails is not None:
        args.since = (datetime.datetime.strptime(args.until, '%Y-%m-%d') -
                      datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        args.min_nr_mails = args.nr_mails
        args.max_nr_mails = args.nr_mails

    if args.cols is None:
        try:
            args.cols = int(os.get_terminal_size().columns * 9 / 10)
        except OSError as e:
            pass

    timestamp = time.time()
    runtime_profile = []
    mails_to_show = []
    msgids = {}
    for idx, source in enumerate(args.sources):
        for mail in get_mails(
                source, args.fetch, args.since, args.until,
                args.min_nr_mails, args.max_nr_mails, None,
                source_type=args.source_type[idx], pisearch=args.pisearch):
            msgid = mail.get_field('message-id')
            if not msgid in msgids:
                mails_to_show.append(mail)
            msgids[msgid] = True
    runtime_profile = [['get_mails', time.time() - timestamp]]
    if args.max_nr_mails is not None:
        mails_to_show = mails_to_show[:args.max_nr_mails]

    to_show, mail_idx_key_map = mails_to_str(
            mails_to_show, MailListFilter(args), MailListDecorator(args), None,
            runtime_profile, args.stat_only, args.stat_authors)
    hkml_cache.writeback_mails()
    cache_list_str(lists_cache_key, to_show, mail_idx_key_map)

    show_list(to_show, args.stdout, args.use_less, mail_idx_key_map)

def add_mails_filter_arguments(parser):
    parser.add_argument(
            '--from_keywords', '--from', metavar='<keyword>', nargs='+',
            help='show mails having the keywords in from: field')
    parser.add_argument(
            '--from_to_keywords', '--from_to', metavar='<keyword>', nargs='+',
            help='same to --from except chekcing to: fields together')
    parser.add_argument(
            '--from_to_cc_keywords', '--from_to_cc', metavar='<keyword>',
            nargs='+',
            help='same to --from except chekcing to: and cc: fields together')
    parser.add_argument('--subject_keywords', '--subject', metavar='<words>',
            type=str, nargs='+',
            help='list mails containing the keyword in their subject')
    parser.add_argument('--body_keywords', '--body', metavar='<keyword>',
            type=str, nargs='+',
            help='list mails containing the keyword in their body')
    parser.add_argument('--new', '-n', action='store_true',
            help='list new threads only')

def add_decoration_arguments(parser):
    parser.add_argument('--collapse', '-c', action='store_true',
            help='collapse threads')
    parser.add_argument('--sort_threads_by', nargs='+',
            choices=['first_date', 'last_date', 'nr_replies', 'nr_comments'],
            default=['last_date'],
            help='threads sort keys')
    parser.add_argument('--ascend', action='store_true',
            help='sort threads in ascending order')
    parser.add_argument('--hot', action='store_true',
            help='show threads having more comments and later updated first.')
    parser.add_argument('--cols', metavar='<int>', type=int,
            help='number of columns for each line')
    parser.add_argument('--url', action='store_true',
            help='print URLs of the mails')
    parser.add_argument('--hide_stat', action='store_true',
            help='hide stat of the mails')
    parser.add_argument('--runtime_profile', action='store_true',
            help='print runtime profiling result')
    parser.add_argument(
            '--max_len_list', metavar='<int>', type=int,
            help='max length of the list')

def set_argparser(parser=None):
    DEFAULT_SINCE = datetime.datetime.now() - datetime.timedelta(days=3)
    DEFAULT_SINCE = DEFAULT_SINCE.strftime('%Y-%m-%d')
    DEFAULT_UNTIL = datetime.datetime.now() + datetime.timedelta(days=1)
    DEFAULT_UNTIL = DEFAULT_UNTIL.strftime('%Y-%m-%d')

    parser.description = 'list mails'
    _hkml.set_manifest_option(parser)
    # What mails to show
    parser.add_argument('sources', metavar='<source of mails>', nargs='*',
            help='  '.join([
            'Source of mails to list.  Could be one of following types.',
            '1) Name of a mailing list in the manifest file.',
            '2) Message-Id of a mail in the thread to list.',
            '3) Path to mbox file in the local filesyste.',
            '4) Special keyword, \'clipboard\'.',
            '\'clipboard\' means mbox string in the clipboard.',
            '5) \'hkml tag\'-added tag.',
            '6) If nothing is given, show last list output.',
            ]))
    parser.add_argument(
            '--source_type', nargs='+',
            choices=['mailing_list', 'msgid', 'mbox', 'clipboard', 'tag'],
            help='type of sources')
    parser.add_argument('--since', metavar='<date>', type=str,
            default=DEFAULT_SINCE,
            help='show mails sent after a specific date. Format: YYYY-MM-DD')
    parser.add_argument('--until', metavar='<date>', type=str,
            default=DEFAULT_UNTIL,
            help='show mails sent before a specific date. Format: YYYY-MM-DD')
    parser.add_argument('--nr_mails', type=int, metavar='<int>',
            help='number of mails to list')
    parser.add_argument('--min_nr_mails', metavar='<int>', type=int,
            default=50,
            help='minimum number of mails to list')
    parser.add_argument('--max_nr_mails', metavar='<int>', type=int,
            help='maximum number of mails to list')
    parser.add_argument('--pisearch', metavar='<query>',
                        help='get mails via given public inbox search query')
    parser.add_argument('--stat_only', action='store_true',
                        help='print statistics only')
    parser.add_argument('--stat_authors', action='store_true',
                        help='print mail authors statistics')

    add_mails_filter_arguments(parser)
    add_decoration_arguments(parser)

    # misc
    parser.add_argument('--fetch', action='store_true',
            help='fetch mails before listing')
    parser.add_argument('--ignore_cache', action='store_true',
            help='ignore cached previous list output')
    parser.add_argument('--stdout', action='store_true',
            help='print to stdout instead of using the pager')
    parser.add_argument('--use_less', action='store_true',
                        help='use \'less\' for output paging')
