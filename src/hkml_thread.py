#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

import _hkml
import hkml_cache
import hkml_list

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

    deduped_mails = []
    msgids = {}
    for mail in mails:
        msgid = mail.get_field('message-id')
        if msgid in msgids:
            continue
        msgids[msgid] = True
        deduped_mails.append(mail)
    return deduped_mails, None

def thread_str(mail_id, dont_use_internet, show_url):
    if mail_id.isdigit():
        mail_id = int(mail_id)
        msgid = None
    else:
        msgid = mail_id

    mails_to_show = None
    if dont_use_internet is False:
        if msgid is None:
            mail = hkml_list.get_mail(mail_id, not_thread_idx=True)
            if mail is None:
                print('wrong <mail_id>')
                exit(1)
            msgid = mail.get_field('message-id')

        mails_to_show, err = get_thread_mails_from_web(msgid)
        if err is not None:
            print(err)
        else:
            mail_id = None
    if mails_to_show is None:
        mails_to_show = hkml_list.last_listed_mails()
        # TODO: Support msgid

    nr_cols_in_line = int(os.get_terminal_size().columns * 9 / 10)
    list_decorator = hkml_list.MailListDecorator(None)
    list_decorator.show_stat = False
    list_decorator.ascend = True,
    list_decorator.sort_threads_by = ['first_date'],
    list_decorator.collapse = False
    list_decorator.show_url = show_url
    list_decorator.cols = nr_cols_in_line
    list_decorator.show_runtime_profile = False

    return hkml_list.mails_to_str(
            mails_to_show, mails_filter=None, list_decorator=list_decorator,
            show_thread_of=mail_id, runtime_profile=[], stat_only=False,
            stat_authors=False)

def main(args):
    if args.mail_id is None:
        to_show, _ = hkml_list.get_last_thread()
        hkml_list.writeback_list_output()
        hkml_list.show_list(to_show, to_stdout=False,
                            to_less=args.no_interactive)
        return

    to_show, mail_idx_key_map = thread_str(args.mail_id,
            args.dont_use_internet, args.url)
    if args.dont_use_internet is False:
        hkml_cache.writeback_mails()
        hkml_list.cache_list_str('thread_output', to_show, mail_idx_key_map)
    hkml_list.show_list(to_show, to_stdout=False, to_less=args.no_interactive)

def set_argparser(parser=None):
    parser.description='list mails of a thread'
    _hkml.set_manifest_option(parser)
    parser.add_argument(
            'mail_id', metavar='<mail identifier>', nargs='?',
            help=' '.join([
                'Identifier of any mail in the thread to list.',
                'Could be the index on the last-generated list or thread,',
                'or the Message-ID of the mail.',
                'If this is not given, shows last thread output.',
                ]))
    parser.add_argument('--url', action='store_true',
            help='print URLs for mails')
    parser.add_argument(
            '--dont_use_internet', action='store_true',
            help='don\'t use internet do get the mails')
    parser.add_argument(
            '--no_interactive', action='store_true',
            help='don\'t use hkml interactive list viewer')
