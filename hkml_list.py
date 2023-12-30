#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile

import _hkml
import hkml_cache
import hkml_fetch
import hkml_open

def lore_url(mail):
    return 'https://lore.kernel.org/r/%s' % mail.get_field('message-id')[1:-1]

def pr_line_wrap(prefix, line, nr_cols, lines):
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
    return threads, by_msgids

def should_open_mail(mail_idx, open_mail_idxs):
    if open_mail_idxs is None:
        return False
    if open_mail_idxs == []:
        return True
    return mail_idx in open_mail_idxs

def pr_mail(mail, suffix, lines,
            open_mail_idxs, show_lore_link, open_mail_via_lore, nr_cols):
    prefix_fields = []
    prefix_fields += ['[%04d]' % mail.pridx]
    indent = ' ' * 4 * mail.prdepth
    prefix_fields.append(indent)
    prefix = ' '.join(prefix_fields)
    subject = '%s' % mail.get_field('subject')
    suffices = [' '.join(mail.get_field('from').split()[0:-1]),
                mail.date.strftime('%m/%d %H:%M')]
    if suffix != '':
        suffices.append(suffix)
    if mail.prdepth and subject.lower().startswith('re: '):
        subject = subject[4:]
    if show_lore_link:
        suffices.append(lore_url(mail))
    suffix = ' (%s)' % ', '.join(suffices)
    pr_line_wrap(prefix, subject + suffix, nr_cols, lines)
    if should_open_mail(mail.pridx, open_mail_idxs):
        lines.append(hkml_open.mail_display_str(mail, open_mail_via_lore,
                                                show_lore_link))

def nr_replies_of(mail):
    nr = len(mail.replies)
    for re in mail.replies:
        nr += nr_replies_of(re)
    return nr

def should_collapse(mail_idx, collapse_threads, expand_threads):
    if not collapse_threads:
        return False
    if expand_threads is None:
        return True
    if expand_threads == []:
        return False
    return not mail_idx in expand_threads

def pr_mails_thread(mail, ls_range, new_threads_only,
                    collapse_threads, expand_threads,
                    open_mail_idxs, show_lore_link, open_mail_via_lore,
                    nr_cols, mail_idx_to_key, lines):
    mail_idx_to_key[mail.pridx] = hkml_cache.get_cache_key(
            mail.gitid, mail.gitdir, mail.get_field('message-id'))

    suffix = ''
    if new_threads_only and mail.get_field('in-reply-to'):
        nr_replies = nr_replies_of(mail)
    if should_collapse(mail.pridx, collapse_threads, expand_threads):
        nr_replies = nr_replies_of(mail)
        suffix = '%d+ msgs' % nr_replies

    if mail.pridx in ls_range:
        pr_mail(mail, suffix, lines,
                open_mail_idxs, show_lore_link, open_mail_via_lore,
                nr_cols)

    if not should_collapse(mail.pridx, collapse_threads, expand_threads):
        for re in mail.replies:
            pr_mails_thread(
                    re, ls_range,
                    new_threads_only, collapse_threads, expand_threads,
                    open_mail_idxs,
                    show_lore_link, open_mail_via_lore, nr_cols,
                    mail_idx_to_key, lines)

def root_of_thread(mail, by_msgids):
    in_reply_to = mail.get_field('in-reply-to')
    if not in_reply_to in by_msgids:
        return mail

    return root_of_thread(by_msgids[in_reply_to], by_msgids)

def thread_index_range(pr_idx, by_pr_idx, by_msgids):
    root = root_of_thread(by_pr_idx[pr_idx], by_msgids)
    if root:
        return range(root.pridx, root.pridx + nr_replies_of(root) + 1)
    return range(0, 0)

def index_of_mail_descr(desc, threads, by_msgids):
    try:
        return int(desc)
    except:
        if desc[0] != '<' or desc[-1] != '>':
            desc = '<%s>' % desc
        if not desc in by_msgids:
            return -1
        return by_msgids[desc].pridx

def mk_pr_ready(mail, list_, depth=0):
    """ Make mails to be all ready for print in list"""
    mail.pridx = len(list_)
    mail.prdepth = depth
    list_.append(mail)
    for mail in mail.replies:
        mk_pr_ready(mail, list_, depth + 1)

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

def mails_to_str(mails_to_show, show_stat, show_thread_of, descend,
        sort_threads_by, new_threads_only, collapse_threads, expand_threads,
        open_mail_idxs, open_mail_via_lore, show_lore_link,
                 nr_cols, mail_idx_to_key):
    lines = []

    threads, by_msgids = threads_of(mails_to_show)
    for sort_category in sort_threads_by:
        sort_threads(threads, sort_category)
    if descend:
        threads.reverse()

    if show_stat:
        nr_new_threads = len([m for m in mails_to_show
            if not m.get_field('in-reply-to')])
        nr_patches = len([m for m in mails_to_show
            if 'patch' in m.tags and not 'reply' in m.tags])
        nr_new_patches = len([m for m in mails_to_show
            if not m.get_field('in-reply-to') and 'patch' in m.tags])
        lines.append('# %d mails, %d threads, %d new threads' %
                (len(mails_to_show), len(threads), nr_new_threads))
        lines.append('# %d patches, %d series' % (nr_patches, nr_new_patches))

    by_pr_idx = []
    for mail in threads:
        mk_pr_ready(mail, by_pr_idx)

    # Show all by default
    ls_range = range(0, 9999)
    if show_thread_of != None:
        index = index_of_mail_descr(show_thread_of, threads, by_msgids)
        if index == -1:
            ls_range = range(0, 0)
        else:
            ls_range = thread_index_range(index, by_pr_idx, by_msgids)

    for mail in threads:
        pr_mails_thread(
                mail, ls_range,
                new_threads_only, collapse_threads, expand_threads,
                open_mail_idxs, show_lore_link, open_mail_via_lore, nr_cols,
                mail_idx_to_key, lines)

    return '\n'.join(lines)

def filter_tags(mail, tags):
    tags_to_show = tags[0]
    tags_to_hide = tags[1]

    has_tag = False
    if tags_to_hide:
        for tag in tags_to_hide:
            if tag.lower() in mail.tags:
                has_tag = True
                break
        if has_tag:
            return False

    if tags_to_show:
        for tag in tags_to_show:
            if tag.lower() in mail.tags:
                has_tag = True
                break
        if not has_tag:
            return False
    return True

def git_log_output_line_to_mail(line, mdir, subject_keyword, body_keyword):
    fields = line.split()
    if len(fields) < 3:
        return None
    subject_offset = len(fields[0]) + 1 + len(fields[1]) + 1
    subject = line[subject_offset:]
    if subject_keyword and not subject_keyword in subject:
        return None
    mail = _hkml.Mail.from_gitlog(fields[0], mdir, fields[1], subject)
    if body_keyword and not body_keyword in mail.get_field('body'):
        return None
    return mail

def get_mails_from_git(manifest, mail_list, since, until, author,
        subject_keyword, body_keyword):
    lines = []
    mdirs = _hkml.mail_list_data_paths(mail_list, manifest)
    if not mdirs:
        print("Mailing list '%s' in manifest not found." % mail_list)
        exit(1)

    mails = []
    for mdir in mdirs:
        if not os.path.isdir(mdir):
            break
        cmd = ['git', '--git-dir=%s' % mdir, 'log',
                '--date=iso-strict', '--pretty=%H %ad %s',
                '--since=%s' % since]
        if until:
            cmd += ['--until=%s' % until]
        if author:
            cmd += ['--author=%s'% author]
        lines = _hkml.cmd_lines_output(cmd)

        for line in lines:
            mail = git_log_output_line_to_mail(line, mdir, subject_keyword,
                    body_keyword)
            if mail:
                mails.append(mail)
    return mails

def filter_mails(manifest, mail_list, since, until, tags, msgid, author,
        subject_keyword, body_keyword):
    manifest = _hkml.get_manifest(manifest)
    if not manifest:
        print('Cannot open manifest file')
        exit(1)

    mails = get_mails_from_git(manifest, mail_list, since, until, author,
            subject_keyword, body_keyword)

    mails_to_show = []
    for mail in mails:
        if msgid and mail.get_field('message-id') != ('<%s>' % msgid):
            continue

        if not filter_tags(mail, tags):
            continue

        mails_to_show.append(mail)

    mails_to_show.reverse()
    return mails_to_show

def get_mails(
        source, fetch, manifest, since, until, show, hide, msgid, author,
        subject_contains, contains):
    if source is None:
        with open(os.path.join(_hkml.get_hkml_dir(), 'mail_idx_to_cache_key'),
                  'r') as f:
            keys = json.load(f).values()
        mails = [hkml_cache.get_mail(key=key) for key in keys]
        return [m for m in mails if m is not None]
    if source == 'clipboard':
        mbox_str = _hkml.cmd_str_output(['xclip', '-o', '-sel', 'clip'])
        mail = _hkml.Mail(mbox=mbox_str)
        if mail.broken():
            print('clipboard is not complete mbox string')
            return []
        return [mail]
    elif os.path.isfile(source):
        return _hkml.read_mbox_file(source)

    if fetch:
        hkml_fetch.fetch_mail(manifest, [source], False, 1)

    return filter_mails(
            manifest, source, since, until, [show, hide], msgid, author,
            subject_contains, contains)

def set_argparser(parser=None):
    DEFAULT_SINCE = datetime.datetime.now() - datetime.timedelta(days=3)
    DEFAULT_SINCE = '%s-%s-%s' % (DEFAULT_SINCE.year, DEFAULT_SINCE.month,
                DEFAULT_SINCE.day)

    _hkml.set_manifest_option(parser)
    parser.add_argument('source', metavar='<source of mails>', nargs='?',
            help='  '.join([
            'Source of mails to read.  Could be one of following types.',
            'Name of a mailing list in the manifest file.',
            'Path to mbox file in the local filesyste.',
            'Special keyword, \'clipboard\'.',
            '\'clipboard\' means mbox string in the clipboard.',
            'No argument means last command listed mails.']))
    parser.add_argument('--since', metavar='<date>', type=str,
            default=DEFAULT_SINCE,
            help='show mails sent after a specific date')
    parser.add_argument('--until', metavar='<date>', type=str,
            help='show mails sent before a specific date')
    parser.add_argument('--show', metavar='<tag>', type=str, nargs='+',
            help='show mails having these tags')
    parser.add_argument('--hide', metavar='<tag>', type=str, nargs='+',
            help='hide mails having these tags')
    parser.add_argument('--msgid', metavar='<message id>', type=str,
            help='show only the mail of the message id')
    parser.add_argument('--author', metavar='<name or email>', type=str,
            help='show only mails from the author')
    parser.add_argument('--subject_contains', metavar='<words>', type=str,
            help='list mails containing the keyword in their subject')
    parser.add_argument('--contains', metavar='<keyword>', type=str,
            help='list mails containing the keyword in their body')

    parser.add_argument('--new', '-n', action='store_true',
            help='list new threads only')
    parser.add_argument('--thread', metavar='<index or msgid>', type=str,
            help='list thread of specific mail')

    parser.add_argument('--descend', action='store_true',
            help='list threads in descending order')
    parser.add_argument('--collapse', '-c', action='store_true',
            help='collapse threads')
    parser.add_argument('--expand', type=int, nargs='*',
            help='expand threads')
    parser.add_argument('--open', '-o', type=int, nargs='*',
            help='show the content of the <index>th mail')
    parser.add_argument('--cols', metavar='<int>', type=int,
            help='number of columns for each line')
    parser.add_argument('--lore', action='store_true',
            help='print lore link for mails')
    parser.add_argument('--lore_read', action='store_true',
            help='fetch body of mail from the lore')
    parser.add_argument('--stat', action='store_true',
            help='show stat of the mails')
    parser.add_argument('--stdout', action='store_true',
            help='print to stdout instead of using the pager')
    parser.add_argument('--fetch', action='store_true',
            help='fetch mails before listing')
    parser.add_argument('--sort_threads_by', nargs='+',
            choices=['first_date', 'last_date', 'nr_replies', 'nr_comments'],
            default=['first_date'],
            help='threads sort field')
    parser.add_argument('--hot', action='store_true',
            help='show latest and hot threds first')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.hot:
        args.descend = True
        args.sort_threads_by = ['last_date', 'nr_comments']
        args.collapse = True

    nr_cols_in_line = args.cols
    if nr_cols_in_line is None:
        try:
            nr_cols_in_line = int(os.get_terminal_size().columns * 9 / 10)
        except OSError as e:
            # maybe user is doing pipe
            nr_cols_in_line = 80

    mails_to_show = get_mails(
            args.source, args.fetch, args.manifest, args.since, args.until,
            args.show, args.hide, args.msgid, args.author,
            args.subject_contains, args.contains)

    if args.thread != None:
        args.collapse = False
    mail_idx_to_key = {}
    to_show = mails_to_str(mails_to_show, args.stat, args.thread,
            args.descend, args.sort_threads_by,
            args.new, args.collapse, args.expand, args.open,
            args.lore_read, args.lore, nr_cols_in_line, mail_idx_to_key)
    hkml_cache.writeback_mails()
    with open(os.path.join(_hkml.get_hkml_dir(), 'mail_idx_to_cache_key'),
              'w') as f:
        json.dump(mail_idx_to_key, f, indent=4)

    if args.stdout:
        print(to_show)
        return
    hkml_open.pr_with_pager_if_needed(to_show)

if __name__ == '__main__':
    main()
