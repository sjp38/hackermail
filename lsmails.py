#!/usr/bin/env python3

import argparse
import datetime
import os
import subprocess
import sys
import tempfile
import time

import _hkml
import fetchmails
import format_reply

new_threads_only = False
descend = False
pr_git_id = False
nr_cols_in_line = 90
collapse_threads = False
show_lore_link = False
open_mail = False
open_mail_via_lore = False
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

def pr_mail_content_via_lore(mail_url):
    try:
        from_lore = _hkml.cmd_lines_output(['w3m', '-dump', mail_url])[3:]
    except:
        sys.stderr.write('\'w3m\' invocation failed.\n')
        exit(1)
    divide_line = '━' * 79
    for line in from_lore:
        if line.strip() == divide_line:
            break
        print(line)

def pr_mail_content(mail, use_lore):
    if use_lore:
        pr_mail_content_via_lore(lore_url(mail))
        return

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
    return threads, by_msgids

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
        pr_mail_content(mail, open_mail_via_lore)
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

def root_of_thread(mail, by_msgids):
    in_reply_to = mail.get_field('in-reply-to')
    if not in_reply_to in by_msgids:
        return mail

    return root_of_thread(by_msgids[in_reply_to], by_msgids)

def thread_index_range(pr_idx, by_pr_idx, by_msgids):
    root = root_of_thread(by_pr_idx[pr_idx], by_msgids)
    if root:
        return [root.pridx, nr_replies_of(root) + 1]
    return [0, 0]

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

def show_mails(mails_to_show, show_stat):
    global show_thread_of
    global ls_range

    threads, by_msgids = threads_of(mails_to_show)
    if descend:
        threads.reverse()

    if show_stat:
        nr_new_threads = len([m for m in mails_to_show
            if not m.get_field('in-reply-to')])
        nr_patches = len([m for m in mails_to_show
            if 'patch' in m.tags and not 'reply' in m.tags])
        nr_new_patches = len([m for m in mails_to_show
            if not m.get_field('in-reply-to') and 'patch' in m.tags])
        print('# %d mails, %d threads, %d new threads' % (len(mails_to_show),
            len(threads), nr_new_threads))
        print('# %d patches, %d series' % (nr_patches, nr_new_patches))

    by_pr_idx = []
    for mail in threads:
        mk_pr_ready(mail, by_pr_idx)

    if show_thread_of != None:
        index = index_of_mail_descr(show_thread_of, threads, by_msgids)
        if index == -1:
            ls_range = [0, 0]
        else:
            ls_range = thread_index_range(index, by_pr_idx, by_msgids)

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

def git_log_output_line_to_mail(line, mdir, subject_keyword, body_keyword):
    fields = line.split()
    if len(fields) < 3:
        return None
    mail = _hkml.Mail.from_gitlog(fields[0], mdir, fields[1], fields[2:])
    if subject_keyword and not subject_keyword in mail.get_field('subject'):
        return None
    if body_keyword and not body_keyword in mail.get_field('body'):
        return None
    return mail

def get_mails_from_git(manifest, mail_list, since, author, subject_keyword,
        body_keyword):
    lines = []
    mdirs = _hkml.mail_list_data_paths(mail_list, manifest)
    if not mdirs:
        print("Mailing list '%s' in manifest '%s' not found." % (
            mail_list, manifest_file))
        exit(1)

    mails = []
    for mdir in mdirs:
        if not os.path.isdir(mdir):
            break
        cmd = ['git', '--git-dir=%s' % mdir, 'log',
                '--date=iso-strict', '--pretty=%h %ad %s',
                '--since=%s' % since]
        if author:
            cmd += ['--author=%s'% author]
        lines = _hkml.cmd_lines_output(cmd)

        for line in lines:
            mail = git_log_output_line_to_mail(line, mdir, subject_keyword,
                    body_keyword)
            if mail:
                mails.append(mail)
    return mails

def filter_mails(manifest, mail_list, since, tags, msgid, author,
        subject_keyword, body_keyword):
    manifest = _hkml.get_manifest(manifest)
    if not manifest:
        print('Cannot open manifest file')
        exit(1)

    mails = get_mails_from_git(manifest, mail_list, since, author,
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

def set_argparser(parser=None):
    DEFAULT_SINCE = datetime.datetime.now() - datetime.timedelta(days=3)
    DEFAULT_SINCE = '%s-%s-%s' % (DEFAULT_SINCE.year, DEFAULT_SINCE.month,
                DEFAULT_SINCE.day)

    _hkml.set_manifest_mlist_options(parser, None)
    parser.add_argument('--since', metavar='<date>', type=str,
            default=DEFAULT_SINCE,
            help='show mails more recent than a specific date')
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
    parser.add_argument('--open', '-o', action='store_true',
            help='show the content of the <index>th mail')
    parser.add_argument('--range', '-r', metavar='<number>', default=[0,-1],
            type=int, nargs='+',
            help='show mails of indexes in given range')
    parser.add_argument('--cols', metavar='<int>', type=int,
            default=nr_cols_in_line, help='number of columns for each line')
    parser.add_argument('--gitid', action='store_true',
            help='print git id of each mail')
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
    parser.add_argument('--repeat', metavar='<int>', type=int, nargs=2,
            default=[0, 1],
            help='delay (seconds) and count for repeated runs')
    parser.add_argument('--reply', action='store_true',
            help='reply to the selected mail')

def main(args=None):
    global new_threads_only
    global show_lore_link
    global open_mail
    global open_mail_via_lore
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
    open_mail_via_lore = args.lore_read
    nr_cols_in_line = args.cols
    pr_git_id = args.gitid
    show_lore_link = args.lore
    ls_range = args.range
    show_thread_of = args.thread
    descend = args.descend
    repeat_delay, repeat_count = args.repeat

    if args.reply == True:
        if repeat_count != 1:
            print('cannot repeat with reply')
            exit(1)
        if len(ls_range) != 1:
            print('cannot reply to multiple mails')
            exit(1)
        args.stdout = False

    if repeat_count != 1:
        args.fetch = True
        args.stdout = True

    if len(ls_range) == 1:
        ls_range.append(1)

    repeated = 0
    while True:
        if args.fetch:
            args.mlist = [args.mlist]
            args.quiet = False
            args.epochs=1
            fetchmails.main(args)
            args.mlist = args.mlist[0]


        mails_to_show = filter_mails(args.manifest, args.mlist, args.since,
                [args.show, args.hide], args.msgid, args.author,
                args.subject_contains, args.contains)

        if not args.stdout:
            orig_stdout = sys.stdout
            fd, tmp_path = tempfile.mkstemp(prefix='hackermail')
            tmp_file = open(tmp_path, 'w')
            sys.stdout = tmp_file

        show_mails(mails_to_show, args.stat)
        repeated += 1
        if repeat_count != 0 and repeated >= repeat_count:
            break
        time.sleep(repeat_delay)

    if not args.stdout:
        sys.stdout = orig_stdout
        tmp_file.close()
        os.close(fd)
        if args.reply == False:
            subprocess.call(['less', tmp_path])
            os.remove(tmp_path)
            exit(0)

        if args.reply == True:
            with open(tmp_path, 'r') as f:
                orig_mbox = f.read()
            os.remove(tmp_path)
            reply_mbox_str = format_reply.format_reply(
                    _hkml.Mail.from_mbox(orig_mbox))
            fd, reply_tmp_path = tempfile.mkstemp(prefix='hkml_reply_')
            with open(reply_tmp_path, 'w') as f:
                f.write(reply_mbox_str)
            if subprocess.call(['vim', reply_tmp_path]) != 0:
                print('editing the reply failed.  The draft is at %s' %
                        reply_tmp_path)
                exit(1)
            with open(reply_tmp_path, 'r') as f:
                print(f.read())
            answer = input('Will send above mail.  Okay? [y/N] ')
            if answer.lower() != 'y':
                answer = input('Leave the draft reply message? [Y/n] ')
                if answer.lower() == 'n':
                    os.remove(reply_tmp_path)
                else:
                    print('Your draft reply message is at %s' % reply_tmp_path)
                exit(0)
            _hkml.cmd_str_output(['git', 'send-email', reply_tmp_path])
            os.remove(reply_tmp_path)

if __name__ == '__main__':
    main()
