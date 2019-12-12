#!/usr/bin/env python3

import argparse
import datetime
import subprocess

import _hckmail

def pr_line_wrap(line, len_indent, nr_cols):
    words = line.split(' ')
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
        print("%s: %s" % (head, mail.mbox_parsed['header'][head.lower()]))
    print("\n%s" % mail.mbox_parsed['body'])
    if show_lore_link and msgid != '':
        print("\nhttps://lore.kernel.org/r/%s\n" % msgid)

def show_mails(mails_to_show, pr_git_id, nr_cols_in_line, threads, nr_skips):
    for idx, mail in enumerate(mails_to_show):
        if idx < nr_skips:
            continue
        indent = ""
        if (mail.series and mail.series[0] > 0) or ('reply' in mail.tags):
            indent = "    "

        # date: <YYYY-MM-DD>T<HH>:<MM>:<SS>+<UTC offset>
        #       e.g., 2019-09-30T09:57:38+08:00
        date = '/'.join(mail.date.split('T')[0].split('-')[1:])
        prefix_fields = ["[%04d]" % idx, date]
        if pr_git_id:
            prefix_fields.append(mail.gitid)
        prefix_fields.append(indent)
        prefix = ' '.join(prefix_fields)

        line = mail.subject
        if len(threads[mail.orig_subject]) > 1:
            line += " (%d+ msgs) " % (len(threads[mail.orig_subject]) - 1)

        pr_line_wrap(prefix + line, len(prefix), nr_cols_in_line)

def set_argparser(parser=None):
    _hckmail.set_mail_search_options(parser, mlist_mandatory=True)
    parser.add_argument('--cols', metavar='cols', type=int, default=130,
            help='Number of columns for each line.')
    parser.add_argument('--gitid', action='store_true',
            help='Print git id of each mail')
    parser.add_argument('--lore', action='store_true',
            help='Print lore link for the <index> mail.')
    parser.add_argument('--skip', metavar='nr_skips', type=int, default=0,
            help='Skips first <nr_skips> mails')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    nr_cols_in_line = args.cols
    pr_git_id = args.gitid
    show_lore_link = args.lore
    nr_skip_mails = args.skip

    if show_lore_link and idx_of_mail == None:
        print("--lore option works with index argument only.\n")
        parser.print_help()
        exit(1)

    mails_to_show, threads = _hckmail.filter_mails(args)

    if len(mails_to_show) == 1:
        show_mail(mails_to_show[0], show_lore_link)
    else:
        show_mails(mails_to_show, pr_git_id, nr_cols_in_line, threads,
                nr_skip_mails)

if __name__ == '__main__':
    main()
