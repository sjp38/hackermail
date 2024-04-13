#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

import _hkml
import hkml_cache
import hkml_list
import hkml_open

def set_argparser(parser=None):
    parser.description='list mails of a thread'
    _hkml.set_manifest_option(parser)
    parser.add_argument(
            'mail_id', metavar='<mail identifier>', nargs='?',
            help=' '.join([
                'Identifier of any mail in the thread to list.',
                'Could be the index on the last-generated list or thread,',
                'or the Message-ID of the mail.'
                'If this is not given, shows last thread output.',
                ]))
    parser.add_argument('--lore', action='store_true',
            help='print lore link for mails')
    parser.add_argument(
            '--dont_use_internet', action='store_true',
            help='don\'t use internet do get the mails')

def get_thread_mails_from_web(msgid):
    if msgid.startswith('<') and msgid.endswith('>'):
        msgid = msgid[1:-1]
    tmp_path = tempfile.mkdtemp(prefix='hkml_thread_')
    pi_url = _hkml.get_manifest()['site']
    down_url = '%s/all/%s/t.mbox.gz' % (pi_url, msgid)
    if subprocess.call(['wget', down_url, '--directory-prefix=%s' % tmp_path],
                       stderr=subprocess.DEVNULL) != 0:
        return None, 'downloading mbox failed'
    if subprocess.call(['gunzip', os.path.join(tmp_path, 't.mbox.gz')]) != 0:
        return None, 'extracting mbox failed'
    mails = hkml_list.get_mails(
            os.path.join(tmp_path, 't.mbox'), False, None, None, None, None)
    os.remove(os.path.join(tmp_path, 't.mbox'))
    os.rmdir(tmp_path)
    return mails, None

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.mail_id is None:
        to_show = hkml_list.get_last_thread_str()
        hkml_open.pr_with_pager_if_needed(to_show)
        hkml_list.writeback_list_output()
        return

    if args.mail_id.isdigit():
        args.mail_id = int(args.mail_id)
        msgid = None
    else:
        msgid = args.mail_id

    mails_to_show = None
    if args.dont_use_internet is False:
        if msgid is None:
            mail = hkml_list.get_mail(args.mail_id, not_thread_idx=True)
            if mail is None:
                print('wrong <mail_id>')
                exit(1)
            msgid = mail.get_field('message-id')

        mails_to_show, err = get_thread_mails_from_web(msgid)
        if err is not None:
            print(err)
        else:
            args.mail_id = None
    if mails_to_show is None:
        mails_to_show = hkml_list.last_listed_mails()
        # TODO: Support msgid

    nr_cols_in_line = int(os.get_terminal_size().columns * 9 / 10)
    list_decorator = hkml_list.MailListDecorator(None)
    list_decorator.show_stat = False
    list_decorator.ascend = True,
    list_decorator.sort_threads_by = ['first_date'],
    list_decorator.collapse = False
    list_decorator.lore = args.lore
    list_decorator.cols = nr_cols_in_line
    list_decorator.show_runtime_profile = False

    to_show = hkml_list.mails_to_str(
            mails_to_show, mails_filter=None, list_decorator=list_decorator,
            show_thread_of=args.mail_id, runtime_profile=[])

    if args.dont_use_internet is False:
        hkml_cache.writeback_mails()
        hkml_list.cache_list_str('thread_output', to_show)
    hkml_open.pr_with_pager_if_needed(to_show)

if __name__ == '__main__':
    main()
