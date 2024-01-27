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
    parser.description='list mails of a thread'
    _hkml.set_manifest_option(parser)
    parser.add_argument(
            'mail_idx', metavar='<mail index>', type=int,
            help='index of any mail in the thread to list')
    parser.add_argument('--lore', action='store_true',
            help='print lore link for mails')
    parser.add_argument(
            '--dont_use_b4', action='store_true',
            help='don\'t use b4 but only previous list\'s output')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if subprocess.call(['which', 'b4'], stdout=subprocess.DEVNULL) == 0:
        use_b4 = args.dont_use_b4 is False

    if use_b4:
        mail = hkml_list.get_mail(args.mail_idx)
        if mail is None:
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
        os.remove(tmp_path)
        args.mail_idx = None
    else:
        mails_to_show = hkml_list.last_listed_mails()

    nr_cols_in_line = int(os.get_terminal_size().columns * 9 / 10)
    to_show = hkml_list.mails_to_str(
            mails_to_show, None, None, None, None, False, args.mail_idx, False,
            ['first_date'], None, None, None, None, args.lore, nr_cols_in_line,
            [], False)

    if use_b4:
        hkml_cache.writeback_mails()
        fake_args = FakeArgs()
        fake_args.source = tmp_path
        list_output_cache_key = hkml_list.args_to_list_output_key(fake_args)
        hkml_list.cache_list_output(list_output_cache_key, to_show)
    hkml_open.pr_with_pager_if_needed(to_show)

if __name__ == '__main__':
    main()
