#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os

import _hkml
import hkml_list
import hkml_open

def set_argparser(parser=None):
    _hkml.set_manifest_option(parser)
    parser.add_argument(
            'mail_idx', metavar='<mail index>', type=int,
            help='list only the thread of the specified mail')
    parser.add_argument('--lore', action='store_true',
            help='print lore link for mails')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    nr_cols_in_line = int(os.get_terminal_size().columns * 9 / 10)

    mails_to_show = hkml_list.last_listed_mails()
    to_show = hkml_list.mails_to_str(
            mails_to_show, None, None, None, None, False, args.mail_idx, False,
            ['first_date'], None, None, None, None, args.lore, nr_cols_in_line,
            [], False)
    hkml_open.pr_with_pager_if_needed(to_show)


if __name__ == '__main__':
    main()
