#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import copy
import datetime
import json
import math
import os
import time

import _hkml
import hkml_cache
import hkml_fetch
import hkml_open

mail_idx_key_cache = None

def get_mail_idx_key_cache():
    global mail_idx_key_cache
    if mail_idx_key_cache is None:
        mail_idx_key_cache = {}
    return mail_idx_key_cache

def get_last_mail_idx_key_cache():
    cache = get_list_output_cache()
    last_key = sorted(cache.keys(), key=lambda x: cache[x]['date'])[-1]
    return cache[last_key]['index_to_cache_key']

def get_mail_cache_key(idx, no_thread_output):
    cache = get_list_output_cache()
    sorted_keys = sorted(cache.keys(), key=lambda x: cache[x]['date'])
    if no_thread_output and sorted_keys[-1] == 'thread_output':
        last_key = sorted_keys[-2]
    else:
        last_key = sorted_keys[-1]
    idx_to_keys = cache[last_key]['index_to_cache_key']
    idx_str = '%d' % idx
    if not idx_str in idx_to_keys:
        return None
    return idx_to_keys[idx_str]

def get_mail(idx, no_thread_output=False):
    return hkml_cache.get_mail(key=get_mail_cache_key(idx, no_thread_output))

def set_mail_cache_key(mail):
    idx = mail.pridx
    key = hkml_cache.get_cache_key(
            mail.gitid, mail.gitdir, mail.get_field('message-id'))

    cache = get_mail_idx_key_cache()
    idx_str = '%d' % idx
    if idx_str in cache:
        return
    cache[idx_str] = key

list_output_cache = None

def list_output_cache_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'list_output_cache')

def args_to_list_output_key(args):
    dict_ = copy.deepcopy(args.__dict__)
    dict_['fetch'] = False
    dict_['stdout'] = False
    del dict_['quiet']

    return json.dumps(dict_, sort_keys=True)

def get_list_output_cache():
    global list_output_cache

    if list_output_cache is None:
        if not os.path.isfile(list_output_cache_file_path()):
            list_output_cache = {}
        else:
            with open(list_output_cache_file_path(), 'r') as f:
                list_output_cache = json.load(f)
    if list_output_cache is None:
        list_output_cache = {}
    return list_output_cache

def writeback_list_output():
    cache = get_list_output_cache()
    with open(list_output_cache_file_path(), 'w') as f:
        json.dump(cache, f, indent=4)

def get_cached_list_output(key):
    cache = get_list_output_cache()
    if not key in cache:
        return None
    cache[key]['date'] = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    return cache[key]['output']

def get_last_list_output():
    cache = get_list_output_cache()
    keys = [k for k in cache if k != 'thread_output']
    key = sorted(keys, key=lambda x: cache[x]['date'])[-1]
    cache[key]['date'] = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    return cache[key]['output']

def get_last_thread_output():
    cache = get_list_output_cache()
    if not 'thread_output' in cache:
        return 'no valid thread output'
    return cache['thread_output']['output']

def invalidate_cached_outputs(source):
    keys_to_del = []
    cache = get_list_output_cache()
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
    cache = get_list_output_cache()
    with open(list_output_cache_file_path(), 'w') as f:
        json.dump(cache, f, indent=4)

def cache_list_output(key, output):
    cache = get_list_output_cache()
    cache[key] = {
            'output': '\n'.join(['# (cached output)', output]),
            'index_to_cache_key': get_mail_idx_key_cache(),
            'date': datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}
    max_cache_sz = 64
    if len(cache) == max_cache_sz:
        keys = sorted(cache.keys(), key=lambda x: cache[x]['date'])
        del cache[keys[0]]
    writeback_list_output_cache()

def lore_url(mail):
    return 'https://lore.kernel.org/r/%s' % mail.get_field('message-id')[1:-1]

def wrap_line(prefix, line, nr_cols):
    lines = []
    words = [prefix] + line.split(' ')
    words_to_print = []
    for w in words:
        words_to_print.append(w)
        line_len = len(' '.join(words_to_print))
        if line_len > nr_cols:
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

def format_entry(mail, max_digits_for_idx, show_nr_replies, show_lore_link,
                 nr_cols):
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
    suffices = [' '.join(from_fields), mail.date.strftime('%y/%m/%d %H:%M')]
    if show_nr_replies:
        suffices.append('%d+ msgs' % nr_replies_of(mail))
    if show_lore_link:
        suffices.append(lore_url(mail))
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

def set_index(mail, list_, depth=0):
    """ Make mails to be all ready for print in list"""
    mail.pridx = len(list_)
    mail.prdepth = depth
    list_.append(mail)

    set_mail_cache_key(mail)

    for mail in mail.replies:
        set_index(mail, list_, depth + 1)

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
    # Treat replies posted within 5 minutes as not comments, but mails sent
    # together by the author, probably the patchset case.
    for reply in mail.replies:
        if (reply.date - mail.date).seconds < 300:
            nr_comments -= 1
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

    def should_filter_out(self, mail):
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

def format_stat(mails_to_show):
    nr_threads = 0
    nr_new_threads = 0
    nr_patches = 0
    nr_patchsets = 0
    oldest = None
    latest = None
    for mail in mails_to_show:
        if mail.parent_mail is None:
            nr_threads += 1
        if not mail.get_field('in-reply-to'):
            nr_new_threads += 1
        if 'patch' in mail.tags and not 'reply' in mail.tags:
            nr_patches += 1
        if 'patch' in mail.tags and not mail.get_field('in-reply-to'):
            nr_patchsets += 1
        if oldest is None or mail.date < oldest.date:
            oldest = mail
        if latest is None or latest.date < mail.date:
            latest = mail

    lines = []
    lines.append('# %d mails, %d threads, %d new threads' %
            (len(mails_to_show), nr_threads, nr_new_threads))
    lines.append('# %d patches, %d series' % (nr_patches, nr_patchsets))
    if oldest is not None:
        lines.append('# oldest: %s' % oldest.date)
        lines.append('# newest: %s' % latest.date)
    return lines

def mails_to_str(
        mails_to_show, mails_filter,
        show_stat, show_thread_of, descend,
        sort_threads_by, collapse_threads,
        show_lore_link, nr_cols, runtime_profile, show_runtime_profile):
    if len(mails_to_show) == 0:
        return 'no mail'

    lines = []

    timestamp = time.time()
    threads = threads_of(mails_to_show)
    for sort_category in sort_threads_by:
        sort_threads(threads, sort_category)
    if descend:
        threads.reverse()
    runtime_profile.append(['threads_extract', time.time() - timestamp])

    by_pr_idx = []
    timestamp = time.time()
    for mail in threads:
        set_index(mail, by_pr_idx)
    runtime_profile.append(['set_index', time.time() - timestamp])

    timestamp = time.time()
    # Show all by default
    if show_thread_of is None:
        start_idx = 0
        end_idx = len(mails_to_show)
    else:
        mail = by_pr_idx[show_thread_of]
        root = root_of_thread(mail)
        start_idx = root.pridx
        end_idx = root.pridx + nr_replies_of(root) + 1
    ls_range = range(start_idx, end_idx)

    max_index = ls_range[-1]
    if max_index == 0:
        max_index = 1
    max_digits_for_idx = math.ceil(math.log(max_index, 10))

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

    for mail in filtered_mails:
        show_nr_replies = False
        if collapse_threads == True:
            if mail.prdepth > 0:
                continue
            show_nr_replies = True
        lines += format_entry(mail, max_digits_for_idx, show_nr_replies,
                              show_lore_link, nr_cols)

    stat_lines = []
    if show_stat:
        total_stat_lines = format_stat(mails_to_show)
        filtered_stat_lines = format_stat(filtered_mails)
        if total_stat_lines == filtered_stat_lines:
            stat_lines += total_stat_lines
        else:
            stat_lines.append('# stat for total mails')
            stat_lines += format_stat(mails_to_show)
            stat_lines.append('#')
            stat_lines.append('# stat for filtered mails')
            stat_lines += format_stat(filtered_mails)

    runtime_profile_lines = []
    total_profiled_time = sum([profile[1] for profile in runtime_profile])
    if show_runtime_profile is True or total_profiled_time > 3:
        runtime_profile.append(['etc', time.time() - timestamp])
        runtime_profile_lines = ['# runtime profile']
        for key, value in runtime_profile:
            runtime_profile_lines.append('# %s: %s' % (key, value))
        runtime_profile_lines.append('#')
    lines = runtime_profile_lines + stat_lines + lines
    return '\n'.join(lines)

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
    mdirs = _hkml.mail_list_data_paths(mail_list, _hkml.get_manifest())
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
            if mail:
                mails.append(mail)
    return mails

def get_mails(source, fetch, since, until,
              min_nr_mails, max_nr_mails, commits_range=None):
    if source == 'clipboard':
        mails, err = _hkml.read_mails_from_clipboard()
        if err != None:
            print('reading mails from clipboard failed: %s' % err)
            exit(1)
        if max_nr_mails is not None:
            mails = mails[:max_nr_mails]
        mails.sort(key=lambda mail: mail.date)
        return mails

    if os.path.isfile(source):
        mails = _hkml.read_mbox_file(source)
        if max_nr_mails is not None:
            mails = mails[:max_nr_mails]
        mails.sort(key=lambda mail: mail.date)
        return mails

    if fetch:
        hkml_fetch.fetch_mail([source], True, 1)

    mails = get_mails_from_git(source, since, until, min_nr_mails,
                               max_nr_mails, commits_range)
    mails.reverse()
    return mails

def last_listed_mails():
    cache = get_list_output_cache()
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

def add_mails_filter_arguments(parser):
    parser.add_argument(
            '--from_keywords', metavar='<keyword>', nargs='+',
            help='show mails having the keywords in from: field')
    parser.add_argument(
            '--from_to_keywords', metavar='<keyword>', nargs='+',
            help='same to --from except chekcing to: fields together')
    parser.add_argument(
            '--from_to_cc_keywords', metavar='<keyword>', nargs='+',
            help='same to --from except chekcing to: and cc: fields together')
    parser.add_argument('--subject_keywords', metavar='<words>', type=str,
            nargs='+',
            help='list mails containing the keyword in their subject')
    parser.add_argument('--body_keywords', metavar='<keyword>', type=str, nargs='+',
            help='list mails containing the keyword in their body')
    parser.add_argument('--new', '-n', action='store_true',
            help='list new threads only')

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
            '2) Path to mbox file in the local filesyste.',
            '3) Special keyword, \'clipboard\'.',
            '\'clipboard\' means mbox string in the clipboard.',
            '4) If nothing is given, show last list output.',
            ]))
    parser.add_argument('--since', metavar='<date>', type=str,
            default=DEFAULT_SINCE,
            help='show mails sent after a specific date')
    parser.add_argument('--until', metavar='<date>', type=str,
            default=DEFAULT_UNTIL,
            help='show mails sent before a specific date')
    parser.add_argument('--nr_mails', type=int, metavar='<int>',
            help='number of mails to list')
    parser.add_argument('--min_nr_mails', metavar='<int>', type=int,
            default=50,
            help='minimum number of mails to list')
    parser.add_argument('--max_nr_mails', metavar='<int>', type=int,
            help='maximum number of mails to list')

    add_mails_filter_arguments(parser)

    # How to show the mails
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

    # misc
    parser.add_argument('--fetch', action='store_true',
            help='fetch mails before listing')

    parser.add_argument('--cols', metavar='<int>', type=int,
            help='number of columns for each line')
    parser.add_argument('--lore', action='store_true',
            help='print lore link for mails')
    parser.add_argument('--hide_stat', action='store_true',
            help='hide stat of the mails')
    parser.add_argument('--stdout', action='store_true',
            help='print to stdout instead of using the pager')
    parser.add_argument('--runtime_profile', action='store_true',
            help='print runtime profiling result')
    parser.add_argument(
            '--quiet', action='store_true',
            help='don\'t display the list but only generate the list')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    list_output_cache_key = args_to_list_output_key(args)
    if args.fetch == False or args.sources == []:
        if args.sources == []:
            to_show = get_last_list_output()
            if to_show is None:
                print('no valid last list output exists')
                exit(1)
        else:
            to_show = get_cached_list_output(list_output_cache_key)
        if to_show is not None:
            if args.quiet is False:
                if args.stdout:
                    print(to_show)
                else:
                    hkml_open.pr_with_pager_if_needed(to_show)
            writeback_list_output()
            return
    else:
        for source in args.sources:
            invalidate_cached_outputs(source)

    if args.hot:
        args.ascend = False
        args.sort_threads_by = ['last_date', 'nr_comments']
        args.collapse = True

    if args.nr_mails is not None:
        args.since = (datetime.datetime.strptime(args.until, '%Y-%m-%d') -
                      datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        args.min_nr_mails = args.nr_mails
        args.max_nr_mails = args.nr_mails

    nr_cols_in_line = args.cols
    if nr_cols_in_line is None:
        try:
            nr_cols_in_line = int(os.get_terminal_size().columns * 9 / 10)
        except OSError as e:
            # maybe user is doing pipe
            nr_cols_in_line = 80

    timestamp = time.time()
    runtime_profile = []
    mails_to_show = []
    for source in args.sources:
        mails_to_show += get_mails(
                source, args.fetch, args.since, args.until,
                args.min_nr_mails, args.max_nr_mails, None)
    runtime_profile = [['get_mails', time.time() - timestamp]]
    if args.max_nr_mails is not None:
        mails_to_show = mails_to_show[:args.max_nr_mails]

    to_show = mails_to_str(
            mails_to_show,
            MailListFilter(args),
            not args.hide_stat, None,
            not args.ascend, args.sort_threads_by,
            args.collapse,
            args.lore, nr_cols_in_line, runtime_profile,
            args.runtime_profile)
    hkml_cache.writeback_mails()
    cache_list_output(list_output_cache_key, to_show)

    if args.quiet:
        return

    if args.stdout:
        print(to_show)
        return
    hkml_open.pr_with_pager_if_needed(to_show)

if __name__ == '__main__':
    main()
