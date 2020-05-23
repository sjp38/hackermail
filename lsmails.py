#!/usr/bin/env python3

import argparse
import datetime
import os
import subprocess
import sys
import tempfile
import time

import _hkml

new_threads_only = False
descend = False
pr_git_id = False
nr_cols_in_line = 100
collapse_threads = False
show_lore_link = False
open_mail = False
ls_range = None
show_thread_of = None

def lore_url(mail):
    return 'https://lore.kernel.org/r/%s' % mail.get_field('message-id')[1:-1]

def pr_line_wrap(prefix, line, nr_cols):
    words = [prefix] + line.split(' ')
    words_to_print = []
    for w in words:
        words_to_print.append(w)
        line_len = len(' '.join(words_to_print))
        if line_len > nr_cols:
            if len(words_to_print) == 1:
                print(words_to_print[0])
            else:
                print(' '.join(words_to_print[:-1]))
                words_to_print = [' ' * (len(prefix) + 1) + words_to_print[-1]]
    print(' '.join(words_to_print))

def pr_mail_content(mail):
    for head in ['Date', 'Subject', 'Message-Id', 'From', 'To', 'CC']:
        value = mail.get_field(head)
        if value:
            print('%s: %s' % (head, value))
    print('\n%s' % mail.get_field('body'))
    if show_lore_link:
        print('\n%s\n' % lore_url(mail))

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
    return threads

def pr_mail_subject(mail, depth, suffix, idx):
    global pr_git_id
    global nr_cols_in_line
    global open_mail

    nr_cols = nr_cols_in_line

    prefix_fields = []
    index = '[%04d]' % idx
    date = '/'.join(mail.git_date.split('T')[0].split('-')[1:])
    prefix_fields += [index, date]
    if pr_git_id:
        prefix_fields.append(mail.gitid)
    indent = ' ' * 4 * depth
    prefix_fields.append(indent)
    prefix = ' '.join(prefix_fields)
    subject = '%s (%s)' % (mail.get_field('subject'),
            ' '.join(mail.get_field('from').split()[0:-1]))
    if depth and subject.lower().startswith('re: '):
        subject = subject[4:]
    if show_lore_link:
        suffix += ' %s' % lore_url(mail)
    if open_mail:
        pr_mail_content(mail)
    else:
        pr_line_wrap(prefix, subject + suffix, nr_cols)

def nr_replies_of(mail):
    nr = len(mail.replies)
    for re in mail.replies:
        nr += nr_replies_of(re)
    return nr

def pr_mails_thread(mail, mail_idx, depth):
    global ls_range
    global open_mail

    nr_printed = 1

    suffix = ''
    if new_threads_only and mail.get_field('in-reply-to'):
        nr_replies = nr_replies_of(mail)
        return nr_printed + nr_replies
    if collapse_threads:
        nr_replies = nr_replies_of(mail)
        suffix = ' (%d+ msgs)' % nr_replies
        nr_printed += nr_replies

    if len(ls_range) == 2:
        start = ls_range[0]
        len_ = ls_range[1]
        end = start + len_
        if len_ == 1:
            open_mail = True
        if mail_idx >= start and (len_ == -1 or mail_idx < end):
            pr_mail_subject(mail, depth, suffix, mail_idx)
    elif mail_idx in ls_range:
            pr_mail_subject(mail, depth, suffix, mail_idx)

    if not collapse_threads:
        for re in mail.replies:
            nr_printed += pr_mails_thread(re, mail_idx + nr_printed, depth + 1)
    return nr_printed

def thread_index_range(mail_index, threads):
    index = 0
    for mail in threads:
        sz_thread = nr_replies_of(mail) + 1
        if mail_index >= index and mail_index < index + sz_thread:
            return [index, sz_thread]
        index += sz_thread
    return [0, 0]

def msgid_to_index(msgid, threads, start_index=0):
    idx = 0
    for mail in threads:
        if mail.get_field('message-id')[1:-1] == msgid:
            return True, start_index + idx
        idx += 1
        found, answer = msgid_to_index(msgid, mail.replies, start_index + idx)
        if found:
            return True, answer
        idx += answer
    return False, idx

def index_of_mail_descr(desc, threads):
    try:
        return int(desc)
    except:
        found, idx = msgid_to_index(desc, threads)
        if not found:
            return -1
        return idx

def show_mails(mails_to_show):
    global show_thread_of
    global ls_range

    threads = threads_of(mails_to_show)
    if descend:
        threads.reverse()

    if show_thread_of != None:
        show_thread_of = index_of_mail_descr(show_thread_of, threads)
        if show_thread_of == -1:
            ls_range = [0, 0]
        else:
            ls_range = thread_index_range(show_thread_of, threads)

    index = 0
    for mail in threads:
        index += pr_mails_thread(mail, index, 0)

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

def get_mails_from_git(manifest, mail_list, since, author=None):
    lines = []
    mdirs = _hkml.mail_list_data_paths(mail_list, manifest)
    if not mdirs:
        print("Mailing list '%s' in manifest '%s' not found." % (
            mail_list, manifest_file))
        exit(1)
    for mdir in mdirs:
        cmd = ['git', '--git-dir=%s' % mdir, 'log',
                '--date=iso-strict', '--pretty=%h %ad %s',
                '--since=%s' % since]
        if author:
            cmd += ['--author=%s'% author]
        lines += _hkml.cmd_lines_output(cmd)

    mails = []
    for line in lines:
        fields = line.split()
        if len(fields) < 3:
            continue
        mails.append(_hkml.Mail.from_gitlog(
            fields[0], mdir, fields[1], fields[2:]))
    return mails

def filter_mails(manifest, mail_list, since, tags, msgid, author):
    manifest = _hkml.get_manifest(manifest)
    if not manifest:
        print('Cannot open manifest file')
        exit(1)

    mails = get_mails_from_git(manifest, mail_list, since, author)

    mails_to_show = []
    for mail in mails:
        if msgid and mail.get_field('message-id') != ('<%s>' % msgid):
            continue

        if not filter_tags(mail, tags):
            continue

        mails_to_show.append(mail)

    mails_to_show.reverse()
    return mails_to_show

def set_argparser(parser=None):
    DEFAULT_SINCE = datetime.datetime.now() - datetime.timedelta(days=3)
    DEFAULT_SINCE = '%s-%s-%s' % (DEFAULT_SINCE.year, DEFAULT_SINCE.month,
                DEFAULT_SINCE.day)

    _hkml.set_manifest_mlist_options(parser, None)
    parser.add_argument('--since', metavar='since', type=str,
            default=DEFAULT_SINCE,
            help='show mails more recent than a specific date')
    parser.add_argument('--show', metavar='tags', type=str, nargs='+',
            help='show mails having these tags')
    parser.add_argument('--hide', metavar='tag', type=str, nargs='+',
            help='hide mails having these tags')
    parser.add_argument('--msgid', metavar='msgid', type=str,
            help='show only the mail of the message id')
    parser.add_argument('--author', metavar='msgid', type=str,
            help='show only mails from the author')
    parser.add_argument('--new', action='store_true',
            help='list new threads only')
    parser.add_argument('--thread', metavar='index', type=str,
            help='list thread of specific mail')

    parser.add_argument('--descend', action='store_true',
            help='list threads in descending order')
    parser.add_argument('--collapse', '-c', action='store_true',
            help='collapse threads')
    parser.add_argument('--open', '-o', action='store_true',
            help='show the content of the <index>th mail')
    parser.add_argument('--range', '-r', metavar='<number>', default=[0,-1],
            type=int, nargs='+',
            help='show mails of indexes in given range')
    parser.add_argument('--cols', metavar='cols', type=int,
            default=nr_cols_in_line, help='number of columns for each line')
    parser.add_argument('--gitid', action='store_true',
            help='print git id of each mail')
    parser.add_argument('--lore', action='store_true',
            help='print lore link for the <index> mail')

def main(args=None):
    global new_threads_only
    global show_lore_link
    global open_mail
    global descend
    global pr_git_id
    global nr_cols_in_line
    global collapse_threads
    global ls_range
    global show_thread_of

    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    new_threads_only = args.new
    collapse_threads = args.collapse
    open_mail = args.open
    nr_cols_in_line = args.cols
    pr_git_id = args.gitid
    show_lore_link = args.lore
    ls_range = args.range
    show_thread_of = args.thread
    descend = args.descend

    if len(ls_range) == 1:
        ls_range.append(1)

    mails_to_show = filter_mails(args.manifest, args.mlist, args.since,
            [args.show, args.hide], args.msgid, args.author)

    fd, tmp_path = tempfile.mkstemp(prefix='hackermail')
    with open(tmp_path, 'w') as tmp_file:
        sys.stdout = tmp_file

        show_mails(mails_to_show)
    subprocess.call(['less', tmp_path])
    os.close(fd)
    os.remove(tmp_path)

if __name__ == '__main__':
    main()
