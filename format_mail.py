#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import tempfile

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
    lines = []
    if not subject:
        subject = '/* write subject here */'
    if not to:
        to = ['/* write recipients here */']
    if not cc:
        cc = ['/* wrtite cc recipients here */']
    lines.append('Subject: %s' % subject)
    if in_reply_to:
        lines.append('In-Reply-To: %s' % in_reply_to)
    for addr in to:
        addr = git_sendemail_valid_recipients(addr)
        lines.append('To: %s' % addr)
    for addr in cc:
        addr = git_sendemail_valid_recipients(addr)
        lines.append('Cc: %s' % addr)
    lines.append('')
    if not body:
        body = '/* write your message here (keep the above blank line) */'
    lines.append(body)
    return '\n'.join(lines)

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
    parser.add_argument('--open_editor', action='store_true',
            help='open a text editor for the mail')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    mbox = format_mbox(args.subject, args.in_reply_to, args.to, args.cc,
        args.body)

    if args.open_editor:
        fd, tmp_path = tempfile.mkstemp(prefix='hkml_mail_')
        with open(tmp_path, 'w') as f:
            f.write(mbox)
        if subprocess.call(['vim', tmp_path]) != 0:
            print('writing mail with editor failed')
            exit(1)
        with open(tmp_path, 'r') as f:
            mbox = f.read()
        os.remove(tmp_path)

    print(mbox)

if __name__ == '__main__':
    main()
