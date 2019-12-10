#!/usr/bin/env python3

import argparse
import datetime
import subprocess

from _hckmail import *

def valid_to_show(mail, tags_to_hide, tags_to_show):
    has_tag = False
    if tags_to_hide:
        for tag in tags_to_hide:
            if tag in mail.tags:
                has_tag = True
                break
        if has_tag:
            return False

    if tags_to_show:
        for tag in tags_to_show:
            if tag in mail.tags:
                has_tag = True
                break
        if not has_tag:
            return False
    return True

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
    DEFAULT_SINCE = datetime.datetime.now() - datetime.timedelta(days=3)
    DEFAULT_SINCE = "%s-%s-%s" % (DEFAULT_SINCE.year, DEFAULT_SINCE.month,
                DEFAULT_SINCE.day)

    parser.add_argument('--manifest', metavar='manifest', type=str,
            default=DEFAULT_MANIFEST,
            help='Manifesto file in grok\'s format plus site field.')
    parser.add_argument('mlist', metavar='mailing list', type=str,
            help='Mailing list to show.')
    parser.add_argument('--since', metavar='since', type=str,
            default=DEFAULT_SINCE,
            help='Show mails more recent than a specific date.')
    parser.add_argument('--show', metavar='tags', type=str,
            help='Tags seperated by comma.  Show mails having the tags.')
    parser.add_argument('--hide', metavar='tag', type=str,
            help='Tags seperated by comma.  Hide mails having the tags.')
    parser.add_argument('--msgid', metavar='msgid', type=str,
            help='Message Id of the mail to show.')
    parser.add_argument('--cols', metavar='cols', type=int, default=130,
            help='Number of columns for each line.')
    parser.add_argument('--gitid', action='store_true',
            help='Print git id of each mail')
    parser.add_argument('content', metavar='idx', type=int, nargs='?',
            help='Show content of specific mail.')
    parser.add_argument('--lore', action='store_true',
            help='Print lore link for the <content> mail.')
    parser.add_argument('--skip', metavar='nr_skips', type=int, default=0,
            help='Skips first <nr_skips> mails')

def filter_mails(manifest, mail_list, since, tags_to_show, tags_to_hide, msgid,
        idx_of_mail, nr_skip_mails):
    mdir = mail_list_data_path(mail_list, manifest)

    cmd = ["git", "--git-dir=%s" % mdir, "log",
            '--date=iso-strict', '--pretty=%h %ad %s (%an)',
            "--since=%s" % since]

    mails_to_show = []
    threads = {} # orig_subject -> mails (latest comes first)
    lines = subprocess.check_output(cmd).decode('utf-8').strip().split('\n')
    for line in lines:
        fields = line.split()
        if len(fields) < 3:
            continue
        mail = Mail(fields[0], mdir, fields[1], fields[2:])

        if msgid and mail.mbox_parsed['header']['message-id'] != (
                '<%s>' % msgid):
            continue

        if not valid_to_show(mail, tags_to_hide, tags_to_show):
            continue

        # Shows only latest reply for given mail
        if mail.orig_subject in threads:
            threads[mail.orig_subject].append(mail)
            if not 'reply' in mail.tags:
                latest_reply = threads[mail.orig_subject][0]
                if latest_reply in mails_to_show:
                    mails_to_show.remove(latest_reply)
                    mails_to_show.append(mail)
            continue
        threads[mail.orig_subject] = [mail]

        mails_to_show.append(mail)

    mails_to_show.reverse()
    return mails_to_show, threads

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    manifest_file = args.manifest
    mail_list = args.mlist
    since = args.since

    tags_to_show = []
    tags_to_hide = []
    if args.show:
        tags_to_show = args.show.split(',')
    if args.hide:
        tags_to_hide = args.hide.split(',')
    msgid = args.msgid

    nr_cols_in_line = args.cols
    pr_git_id = args.gitid
    idx_of_mail = args.content
    show_lore_link = args.lore
    nr_skip_mails = args.skip

    manifest = get_manifest(manifest_file)
    if not manifest:
        print("Cannot open manifest file %s" % manifest_file)
        parser.print_help()
        exit(1)

    if show_lore_link and idx_of_mail == None:
        print("--lore option works with content argument only.\n")
        parser.print_help()
        exit(1)

    mails_to_show, threads = filter_mails(manifest, mail_list, since,
            tags_to_show, tags_to_hide, msgid, idx_of_mail, nr_skip_mails)

    if idx_of_mail != None:
        show_mail(mails_to_show[idx_of_mail], show_lore_link)
    elif len(mails_to_show) == 1:
        show_mail(mails_to_show[0], show_lore_link)
    else:
        show_mails(mails_to_show, pr_git_id, nr_cols_in_line, threads,
                nr_skip_mails)

if __name__ == '__main__':
    main()
