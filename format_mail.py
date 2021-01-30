#!/usr/bin/env python3

import argparse
import subprocess
import sys

import _hkml

def git_sendemail_valid_recipients(recipients):
    """each line should be less than 998 char"""
    if not recipients:
        return ''
    # TODO: Could name contain ','?
    if len(recipients) < 998:
        return recipients

    addresses = recipients.split(',')
    lines = []
    line = ''
    for addr in addresses[1:]:
        if len(line) + len(addr) + len(', ') > 998:
            lines.append(line)
            line = '\t'
        line += '%s,' % addr
    lines.append(line)
    lines[-1] = lines[-1][:-1]
    return '\n'.join(lines)

def format_mbox(subject, in_reply_to, to, cc, body):
    if not subject:
        subject = '/* write subject here */'
    if not to:
        to = ['/* write recipients here */']
    if not cc:
        cc = ['/* wrtite cc recipients here */']
    print('Subject: %s' % subject)
    if in_reply_to:
        print('In-Reply-To: %s' % in_reply_to)
    for addr in to:
        addr = git_sendemail_valid_recipients(addr)
        print('To: %s' % addr)
    for addr in cc:
        addr = git_sendemail_valid_recipients(addr)
        print('Cc: %s' % addr)
    print('')
    if not body:
        body = '/* write your message here (keep the above blank line) */'
    print(body)

def set_argparser(parser=None):
    parser.add_argument('--subject', metavar='<subject>', type=str,
            help='Subject of the mail.')
    parser.add_argument('--in-reply-to', metavar='<message id>',
            help='Add in-reply-to field in the mail header')
    parser.add_argument('--to', metavar='<email address>', nargs='+',
            help='recipients of the mail')
    parser.add_argument('--cc', metavar='<email address>', nargs='+',
            help='cc recipients of the mail')
    parser.add_argument('--body', metavar='<body>',
            help='body message of the mail')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    format_mbox(args.subject, args.in_reply_to, args.to, args.cc, args.body)

if __name__ == '__main__':
    main()
