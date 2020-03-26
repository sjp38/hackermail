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

def show_mail(mail):
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

show_lore_link = False
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
    if show_lore_link:
        suffix += ' https://lore.kernel.org/r/%s' % (
                mail.get_field('message-id')[1:-1])
    pr_line_wrap(prefix, subject + suffix, nr_cols)
    if open_mail:
        print('')
        show_mail(mail)

def pr_thread_mail(mail, depth, nr_skips, pr_git_id, nr_cols):
    pr_mail_subject(mail, depth, nr_skips, pr_git_id, nr_cols)
    for re in mail.replies:
        pr_thread_mail(re, depth + 1, nr_skips, pr_git_id, nr_cols)

def nr_replies_of(mail):
    nr = len(mail.replies)
    for re in mail.replies:
        nr += nr_replies_of(re)
    return nr

def show_mails(mails_to_show, pr_git_id, nr_cols_in_line, nr_skips,
        collapse_threads):
    threads = threads_of(mails_to_show)
    for mail in threads:
        if collapse_threads:
            suffix = ' (%d+ msgs)' % nr_replies_of(mail)
            pr_mail_subject(mail, 0, nr_skips, pr_git_id, nr_cols_in_line,
                    suffix)
        else:
            pr_thread_mail(mail, 0, nr_skips, pr_git_id, nr_cols_in_line)

def filter_tags(mail, tags_to_hide, tags_to_show):
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
        cmd = ["git", "--git-dir=%s" % mdir, "log",
                '--date=iso-strict', '--pretty=%h %ad %s (%an)',
                "--since=%s" % since]
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

def filter_mails(args):
    mail_list = args.mlist
    since = args.since
    tags_to_show = args.show
    tags_to_hide = args.hide
    msgid = args.msgid

    manifest = _hkml.get_manifest(args.manifest)
    if not manifest:
        print("Cannot open manifest file %s" % args.manifest)
        exit(1)

    mails = get_mails_from_git(manifest, mail_list, since, args.author)

    mails_to_show = []
    for mail in mails:
        if msgid and mail.get_field('message-id') != ('<%s>' % msgid):
            continue

        if not filter_tags(mail, tags_to_hide, tags_to_show):
            continue

        mails_to_show.append(mail)

    mails_to_show.reverse()
    return mails_to_show

def set_argparser(parser=None):
    DEFAULT_SINCE = datetime.datetime.now() - datetime.timedelta(days=3)
    DEFAULT_SINCE = "%s-%s-%s" % (DEFAULT_SINCE.year, DEFAULT_SINCE.month,
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

    parser.add_argument('--collapse', action='store_true',
            help='collapse threads')
    parser.add_argument('--open', '-o', action='store_true',
            help='show the content of the <index>th mail')
    parser.add_argument('--skip', '-s', metavar='nr_skips', type=int, default=0,
            help='skips first <nr_skips> mails')
    parser.add_argument('--cols', metavar='cols', type=int, default=130,
            help='number of columns for each line')
    parser.add_argument('--gitid', action='store_true',
            help='print git id of each mail')
    parser.add_argument('--lore', action='store_true',
            help='print lore link for the <index> mail')

def main(args=None):
    global show_lore_link
    global open_mail

    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    collapse_threads = args.collapse
    open_mail = args.open
    nr_cols_in_line = args.cols
    pr_git_id = args.gitid
    show_lore_link = args.lore
    nr_skip_mails = args.skip

    mails_to_show = filter_mails(args)

    tmp_path = tempfile.mkstemp()[1]
    with open(tmp_path, 'w') as tmp_file:
        sys.stdout = tmp_file

        if len(mails_to_show) == 1:
            show_mail(mails_to_show[0])
        else:
            show_mails(mails_to_show, pr_git_id, nr_cols_in_line,
                    nr_skip_mails, collapse_threads)
    subprocess.call(['less', tmp_path])
    os.remove(tmp_path)

if __name__ == '__main__':
    main()
