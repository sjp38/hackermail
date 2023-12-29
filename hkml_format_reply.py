#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import subprocess
import sys

import _hkml
import hkml_write

def set_argparser(parser=None):
    parser.add_argument('mbox_file', metavar='<file>', type=str, nargs='?',
            help='Mbox format file of the mail to format reply for.')
    parser.add_argument('--mbox_url', metavar='<url>',
            help='Mbox format string url. e.g., lore \'raw\' link')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.mbox_file:
        with open(args.mbox_file, 'r') as f:
            mbox = f.read()
    elif args.mbox_url:
        mbox = _hkml.cmd_str_output(['curl', args.mbox_url])
    else:
        mbox = sys.stdin.read()
    print(format_reply(_hkml.Mail.from_mbox(mbox)))

if __name__ == '__main__':
    main()
