#!/usr/bin/env python3

import argparse
import datetime
import os
import subprocess
import sys
import tempfile

import _hkml
import hkml_cache
import hkml_format_reply
import hkml_fetch
import hkml_send

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

def pr_mail_content_via_lore(mail_url, lines):
    try:
        from_lore = _hkml.cmd_lines_output(['w3m', '-dump', mail_url])[3:]
    except:
        sys.stderr.write('\'w3m\' invocation failed.\n')
        exit(1)
    divide_line = '━' * 79
    for line in from_lore:
        if line.strip() == divide_line:
            break
        lines.append(line)

def pr_mail_content(mail, use_lore, show_lore_link, lines):
    if use_lore:
        pr_mail_content_via_lore(lore_url(mail), lines)
        return

    for head in ['Date', 'Subject', 'Message-Id', 'From', 'To', 'CC']:
        value = mail.get_field(head)
        if value:
            lines.append('%s: %s' % (head, value))
    lines.append('\n%s' % mail.get_field('body'))
    if show_lore_link:
        lines.append('\n%s\n' % lore_url(mail))

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

def pr_mail(mail, depth, suffix, idx, lines, pr_subject, pr_git_id,
            open_mail_idxs, show_lore_link, open_mail_via_lore, nr_cols):
    prefix_fields = []
    index = '[%04d]' % idx
    date = '%d/%d' % (mail.date.month, mail.date.day)
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
    if should_open_mail(idx, open_mail_idxs):
        if pr_subject:
            pr_line_wrap(prefix, subject + suffix, nr_cols, lines)
        pr_mail_content(mail, open_mail_via_lore, show_lore_link, lines)
    else:
        pr_line_wrap(prefix, subject + suffix, nr_cols, lines)

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

def pr_mails_thread(mail, mail_idx, depth, ls_range, new_threads_only,
                    collapse_threads, expand_threads, pr_git_id,
                    open_mail_idxs, show_lore_link, open_mail_via_lore,
                    nr_cols, lines):
    nr_printed = 1

    suffix = ''
    if new_threads_only and mail.get_field('in-reply-to'):
        nr_replies = nr_replies_of(mail)
        return nr_printed + nr_replies
    if should_collapse(mail_idx, collapse_threads, expand_threads):
        nr_replies = nr_replies_of(mail)
        suffix = ' (%d+ msgs)' % nr_replies
        nr_printed += nr_replies

    if len(ls_range) == 2:
        start = ls_range[0]
        len_ = ls_range[1]
        end = start + len_
        if len_ == 1:
            open_mail_idxs = [start]
        if mail_idx >= start and (len_ == -1 or mail_idx < end):
            pr_mail(mail, depth, suffix, mail_idx, lines, len_ > 1, pr_git_id,
                    open_mail_idxs, show_lore_link, open_mail_via_lore,
                    nr_cols)
    elif mail_idx in ls_range:
            pr_mail(mail, depth, suffix, mail_idx, lines, len(ls_range) > 1,
                    pr_git_id, open_mail_idxs,
                    show_lore_link, open_mail_via_lore, nr_cols)

    if not should_collapse(mail_idx, collapse_threads, expand_threads):
        for re in mail.replies:
            nr_printed += pr_mails_thread(
                    re, mail_idx + nr_printed, depth + 1, ls_range,
                    new_threads_only, collapse_threads, expand_threads,
                    pr_git_id, open_mail_idxs,
                    show_lore_link, open_mail_via_lore, nr_cols, lines)
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

def mails_to_str(mails_to_show, show_stat, show_thread_of, ls_range, descend,
        sort_threads_by, new_threads_only, collapse_threads, expand_threads,
        pr_git_id, open_mail_idxs, open_mail_via_lore, show_lore_link,
                 nr_cols):
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

    if show_thread_of != None:
        index = index_of_mail_descr(show_thread_of, threads, by_msgids)
        if index == -1:
            ls_range = [0, 0]
        else:
            ls_range = thread_index_range(index, by_pr_idx, by_msgids)

    index = 0
    for mail in threads:
        index += pr_mails_thread(
                mail, index, 0, ls_range,
                new_threads_only, collapse_threads, expand_threads, pr_git_id,
                open_mail_idxs, show_lore_link, open_mail_via_lore, nr_cols,
                lines)

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
                '--date=iso-strict', '--pretty=%h %ad %s',
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
    if source == 'clipboard':
        mbox_str = _hkml.cmd_str_output(['xclip', '-o', '-sel', 'clip'])
        return [_hkml.Mail.from_mbox(mbox_str)]
    elif os.path.isfile(source):
        return _hkml.read_mbox_file(source)

    if fetch:
        hkml_fetch.fetch_mail(manifest, [source], False, 1)

    return filter_mails(
            manifest, source, since, until, [show, hide], msgid, author,
            subject_contains, contains)

def write_send_reply(orig_mbox):
    reply_mbox_str = hkml_format_reply.format_reply(
            _hkml.Mail.from_mbox(orig_mbox))
    fd, reply_tmp_path = tempfile.mkstemp(prefix='hkml_reply_')
    with open(reply_tmp_path, 'w') as f:
        f.write(reply_mbox_str)
    if subprocess.call(['vim', reply_tmp_path]) != 0:
        print('editing the reply failed.  The draft is at %s' %
                reply_tmp_path)
        exit(1)
    hkml_send.send_mail(reply_tmp_path, get_confirm=True)
    os.remove(reply_tmp_path)
    return

def set_argparser(parser=None):
    DEFAULT_SINCE = datetime.datetime.now() - datetime.timedelta(days=3)
    DEFAULT_SINCE = '%s-%s-%s' % (DEFAULT_SINCE.year, DEFAULT_SINCE.month,
                DEFAULT_SINCE.day)

    _hkml.set_manifest_option(parser)
    parser.add_argument('source', metavar='<source of mails>',
            help='  '.join([
            'Source of mails to read.  Could be one of following types.',
            'Name of a mailing list in the manifest file.',
            'Path to mbox file in the local filesyste.',
            'Special keyword, \'clipboard\'.',
            '\'clipboard\' means mbox string in the clipboard.']))
    parser.add_argument('--since', metavar='<date>', type=str,
            default=DEFAULT_SINCE,
            help='show mails more recent than a specific date')
    parser.add_argument('--until', metavar='<date>', type=str,
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
    parser.add_argument('--expand', type=int, nargs='*',
            help='expand threads')
    parser.add_argument('--open', '-o', type=int, nargs='*',
            help='show the content of the <index>th mail')
    parser.add_argument('--range', '-r', metavar='<number>', default=[0,-1],
            type=int, nargs='+',
            help='show mails of indexes in given range')
    parser.add_argument('--cols', metavar='<int>', type=int,
            help='number of columns for each line')
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
    parser.add_argument('--reply', type=int, metavar='<int>',
            help='reply to the selected mail')
    parser.add_argument('--sort_threads_by', nargs='+',
            choices=['first_date', 'last_date', 'nr_replies', 'nr_comments'],
            default=['first_date'],
            help='threads sort field')
    parser.add_argument('--export', metavar='<file>',
            help='export fetched mails to a file')
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

    ls_range = args.range

    if args.reply is not None:
        ls_range = [args.reply]

    if len(ls_range) == 1:
        ls_range.append(1)

    mails_to_show = get_mails(
            args.source, args.fetch, args.manifest, args.since, args.until,
            args.show, args.hide, args.msgid, args.author,
            args.subject_contains, args.contains)

    if args.export:
        return _hkml.export_mails(mails_to_show, args.export)

    if args.thread != None:
        args.collapse = False
    to_show = mails_to_str(mails_to_show, args.stat, args.thread, ls_range,
            args.descend, args.sort_threads_by,
            args.new, args.collapse, args.expand, args.gitid, args.open,
            args.lore, args.lore_read, nr_cols_in_line)
    hkml_cache.write_mails_cache_file()

    if args.reply is not None:
        return write_send_reply(to_show)

    try:
        if len(to_show.split('\n')) < os.get_terminal_size().lines:
            args.stdout = True
    except OSError as e:
        # maybe the user is using pipe to the output
        pass

    if args.stdout:
        print(to_show)
        return

    fd, tmp_path = tempfile.mkstemp(prefix='hackermail')
    with open(tmp_path, 'w') as f:
        f.write(to_show)
    subprocess.call(['less', tmp_path])
    os.remove(tmp_path)
    exit(0)

if __name__ == '__main__':
    main()
