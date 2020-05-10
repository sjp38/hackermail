#!/usr/bin/env python3

import argparse
import subprocess
import sys

import _hkml

def format_mbox(subject, to, cc):
    if not subject:
        subject = '/* write subject here */'
    if not to:
        to = ['/* write recipients here */']
    if not cc:
        cc = ['/* wrtite cc recipients here */']
    print('Subject: %s' % subject)
    for addr in to:
        print('To: %s' % addr)
    for addr in cc:
        print('Cc: %s' % addr)
    print('')
    print('/* write your message here (keep the above blank line) */')

def set_argparser(parser=None):
    parser.add_argument('--subject', metavar='subject', type=str,
            help='Subject of the mail.')
    parser.add_argument('--to', metavar='email address', nargs='+',
            help='recipients of the mail')
    parser.add_argument('--cc', metavar='email address', nargs='+',
            help='cc recipients of the mail')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    format_mbox(args.subject, args.to, args.cc)

if __name__ == '__main__':
    main()
