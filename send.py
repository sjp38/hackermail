#!/usr/bin/env python3

import argparse
import subprocess

import _hkml

def set_argparser(parser=None):
    parser.add_argument('mbox_file', metavar='mboxfile',
            help='Mbox format file of the mail to send.')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    mboxfile = args.mbox_file

    _hkml.cmd_str_output(['git', 'send-email', mboxfile])

if __name__ == '__main__':
    main()
