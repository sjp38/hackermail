#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import subprocess
import sys
import tempfile

import _hkml
import hkml_list
import hkml_send

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

def format_mbox(subject, in_reply_to, to, cc, body, from_, draft,
                attach_file=None):
    if draft is not None:
        mail = hkml_list.get_mail(draft)
        if mail is None:
            print('failed getting draft mail of the index.')
            exit(1)
        lines = []
        for line in mail.mbox.split('\n')[1:]:
            if line.startswith('Message-ID: '):
                continue
            if line.startswith('Date: '):
                continue
            lines.append(line)
        return '\n'.join(lines)

    lines = []
    if not subject:
        subject = '/* write subject here */'
    if not to:
        to = ['/* write recipients here */']
    if not cc:
        cc = ['/* wrtite cc recipients here */']
    if from_ is None:
        for conf in ['sendemail.from', 'user.email']:
            try:
                from_ = subprocess.check_output(
                        ['git', 'config', conf]).decode().strip()
                break
            except:
                pass

        if from_ is None:
            from_ = '/* fill up please */'

    lines.append('Subject: %s' % subject)
    lines.append('From: %s' % from_)
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

    if attach_file is not None:
        with open(attach_file, 'r') as f:
            lines.append('\n%s\n%s' % ('=' * 79, f.read()))
    return '\n'.join(lines)

def main(args):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    mbox = format_mbox(args.subject, args.in_reply_to, args.to, args.cc,
        args.body, None, args.draft)

    if args.format_only:
        print(mbox)
        return

    fd, tmp_path = tempfile.mkstemp(prefix='hkml_mail_')
    with open(tmp_path, 'w') as f:
        f.write(mbox)
    if subprocess.call(['vim', tmp_path]) != 0:
        print('writing mail with editor failed')
        exit(1)
    hkml_send.send_mail(tmp_path, get_confirm=True)

def set_argparser(parser=None):
    parser.description = 'write a mail'
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
    parser.add_argument('--format_only', action='store_true',
            help='print formatted mail template only')
    parser.add_argument('--draft', metavar='<index>', type=int,
                        help='resume writing from the given draft')
