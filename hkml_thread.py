#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

import _hkml
import hkml_cache
import hkml_list
import hkml_open

class FakeArgs:
    pass

def set_argparser(parser=None):
    _hkml.set_manifest_option(parser)
    parser.add_argument(
            'mail_idx', metavar='<mail index>', type=int,
            help='list only the thread of the specified mail')
    parser.add_argument('--lore', action='store_true',
            help='print lore link for mails')
    parser.add_argument(
            '--above_list', action='store_true',
            help='list whole thread, above the last generated list')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    nr_cols_in_line = int(os.get_terminal_size().columns * 9 / 10)

    mails_to_show = hkml_list.last_listed_mails()

    if args.above_list:
        found = False
        for mail in mails_to_show:
            if mail.pridx == args.mail_idx:
                found = True
                break
        if found is False:
            print('wrong <mail_idx>')
            exit(1)
        msgid = mail.get_field('message-id')

        fd, tmp_path = tempfile.mkstemp(prefix='hkml_thread_')
        if subprocess.call(['b4', 'mbox', '--mbox-name', tmp_path, msgid],
                           stderr=subprocess.DEVNULL) != 0:
            print('b4 mbox failed')
            exit(1)
        mails_to_show = hkml_list.get_mails(
                tmp_path, False, None, None, None, None, None)
        args.mail_idx = None

    to_show = hkml_list.mails_to_str(
            mails_to_show, None, None, None, None, False, args.mail_idx, False,
            ['first_date'], None, None, None, None, args.lore, nr_cols_in_line,
            [], False)

    if args.above_list:
        hkml_cache.writeback_mails()
        fake_args = FakeArgs()
        fake_args.source = tmp_path
        list_output_cache_key = hkml_list.args_to_list_output_key(fake_args)
        hkml_list.cache_list_output(list_output_cache_key, to_show)
    hkml_open.pr_with_pager_if_needed(to_show)

    os.remove(tmp_path)

if __name__ == '__main__':
    main()
