#!/usr/bin/env python3

import argparse
import datetime
import os
import subprocess
import sys
import tempfile
import time

import _hkml

def pr_line_wrap(prefix, line, nr_cols):
    len_indent = len(prefix)
    words = [prefix] + line.split(' ')
    line = ""
    words_to_print = []
    for w in words:
        words_to_print.append(w)
        line_len = len(' '.join(words_to_print))
        if line_len > nr_cols:
            if len(words_to_print) == 1:
                print(words_to_print[0])
            else:
                print(' '.join(words_to_print[:-1]))
                words_to_print = [' ' * len_indent + words_to_print[-1]]
    print(' '.join(words_to_print))

def show_mail(mail, show_lore_link):
    for head in ['Date', 'Subject', 'Message-Id', 'From', 'To', 'CC']:
        value = mail.get_field(head)
        if value:
            print("%s: %s" % (head, value))
    print("\n%s" % mail.get_field('body'))
    if show_lore_link:
        print("\nhttps://lore.kernel.org/r/%s\n" %
                mail.get_field('message-id'))

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

open_mail = False
idx = 0
def pr_mail_subject(mail, depth, nr_skips, pr_git_id, nr_cols, suffix=''):
    global idx

    if idx < nr_skips:
        idx += 1
        return

    prefix_fields = []
    index = '[%04d]' % idx
    idx += 1
    date = '/'.join(mail.git_date.split('T')[0].split('-')[1:])
    prefix_fields += [index, date]
    if pr_git_id:
        prefix_fields.append(mail.gitid)
    indent = ' ' * 4 * depth
    prefix_fields.append(indent)
    prefix = ' '.join(prefix_fields)
    subject = mail.get_field('subject')
    if depth and subject.lower().startswith('re: '):
        subject = subject[4:]
    pr_line_wrap(prefix, subject + suffix, nr_cols)
    if open_mail:
        print('')
        show_mail(mail, True)

def pr_thread_mail(mail, depth, nr_skips, pr_git_id, nr_cols):
    pr_mail_subject(mail, depth, nr_skips, pr_git_id, nr_cols)
    for re in mail.replies:
        pr_thread_mail(re, depth + 1, nr_skips, pr_git_id, nr_cols)

def nr_replies_of(mail):
    nr = len(mail.replies)
    for re in mail.replies:
        nr += nr_replies_of(re)
    return nr

def show_mails(mails_to_show, pr_git_id, nr_cols_in_line, threads, nr_skips,
        show_threads_form, collapse_threads):
    if show_threads_form:
        threads = threads_of(mails_to_show)
        for mail in threads:
            if collapse_threads:
                suffix = ' (%d+ msgs) ' % nr_replies_of(mail)
                pr_mail_subject(mail, 0, nr_skips, pr_git_id, nr_cols_in_line,
                        suffix)
            else:
                pr_thread_mail(mail, 0, nr_skips, pr_git_id, nr_cols_in_line)
        return

    for idx, mail in enumerate(mails_to_show):
        depth = 0
        if (mail.series and mail.series[0] > 0) or ('reply' in mail.tags):
            depth = 1

        suffix = ''
        if len(threads[mail.orig_subject]) > 1:
            suffix = " (%d+ msgs) " % (len(threads[mail.orig_subject]) - 1)
        pr_mail_subject(mail, depth, nr_skips, pr_git_id, nr_cols_in_line,
                suffix)

def set_argparser(parser=None):
    _hkml.set_mail_search_options(parser, mlist_nargs=None)
    parser.add_argument('--threads', action='store_true',
            help='Print in threads format')
    parser.add_argument('--collapse', action='store_true',
            help='Collapse threads')
    parser.add_argument('--open', action='store_true',
            help='Show the content of the <index>th mail')
    parser.add_argument('--cols', metavar='cols', type=int, default=130,
            help='Number of columns for each line.')
    parser.add_argument('--gitid', action='store_true',
            help='Print git id of each mail')
    parser.add_argument('--lore', action='store_true',
            help='Print lore link for the <index> mail.')
    parser.add_argument('--skip', metavar='nr_skips', type=int, default=0,
            help='Skips first <nr_skips> mails')
    parser.add_argument('--livestream', action='store_true',
            help='List mails in livestream.')

def do_livestream(args):
    nr_skip_mails = args.skip
    while True:
        args.quiet = False
        if not args.manifest:
            args.manifest = os.path.join(_hkml.get_hkml_dir(), 'manifest')
        _hkml.fetch_mail(args.manifest, [args.mlist], True)
        mails_to_show, threads = _hkml.filter_mails(args)
        show_mails(mails_to_show, args.gitid, args.cols, threads,
                nr_skip_mails, False)
        if not mails_to_show or nr_skip_mails == len(mails_to_show):
            sys.stdout.write('.')
            sys.stdout.flush()
        else:
            print('')
        nr_skip_mails = len(mails_to_show)
        time.sleep(10)

def main(args=None):
    global open_mail

    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    show_threads_form = args.threads
    collapse_threads = args.collapse
    open_mail = args.open
    nr_cols_in_line = args.cols
    pr_git_id = args.gitid
    show_lore_link = args.lore
    nr_skip_mails = args.skip
    livestream = args.livestream

    # TODO: Clean up
    if livestream:
        do_livestream(args)
        return

    if show_lore_link and idx_of_mail == None:
        print("--lore option works with index argument only.\n")
        parser.print_help()
        exit(1)

    mails_to_show, threads = _hkml.filter_mails(args)

    tmp_path = tempfile.mkstemp()[1]
    with open(tmp_path, 'w') as tmp_file:
        sys.stdout = tmp_file

        if len(mails_to_show) == 1:
            show_mail(mails_to_show[0], show_lore_link)
        else:
            show_mails(mails_to_show, pr_git_id, nr_cols_in_line, threads,
                    nr_skip_mails, show_threads_form, collapse_threads)
    subprocess.call(['less', tmp_path])
    os.remove(tmp_path)

if __name__ == '__main__':
    main()
