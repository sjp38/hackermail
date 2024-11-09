#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import subprocess
import sys
import tempfile

import _hkml
import _hkml_list_cache
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

def get_git_config(config_name):
    try:
        result = subprocess.check_output(
                ['git', 'config', config_name]).decode().strip()
        return result, None
    except Exception as e:
        return None, '"git config %s" failed (%s)' % (config_name, e)

def format_mbox(subject, in_reply_to, to, cc, body, from_, draft_mail,
                attach_files=None):
    if draft_mail is not None:
        lines = []
        for line in draft_mail.mbox.split('\n')[1:]:
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
        from_, err = get_git_config('sendemail.from')
        if err is not None:
            name, err = get_git_config('user.name')
            email, err = get_git_config('user.email')
            if email is None:
                from_ = '/* fill up please */'
            else:
                from_ = '%s <%s>' % (name, email)

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

    if attach_files is not None:
        for idx, attach_file in enumerate(attach_files):
            marker_line = '==== Attachment %d (%s) ====' % (idx, attach_file)
            with open(attach_file, 'r') as f:
                lines.append('\n%s\n%s' % (marker_line, f.read()))
    return '\n'.join(lines)

def write_send_mail(draft_mail, subject, in_reply_to, to, cc, body, attach,
                    format_only):
    mbox = format_mbox(subject, in_reply_to, to, cc, body, None, draft_mail,
                       attach)

    if format_only:
        print(mbox)
        return

    fd, tmp_path = tempfile.mkstemp(prefix='hkml_mail_')
    with open(tmp_path, 'w') as f:
        f.write(mbox)
    if subprocess.call(['vim', tmp_path]) != 0:
        print('writing mail with editor failed')
        exit(1)
    hkml_send.send_mail(tmp_path, get_confirm=True)

def main(args):
    draft_mail = None
    if args.draft is not None:
        draft_mail = _hkml_list_cache.get_mail(args.draft)
        if draft_mail is None:
            print('failed getting draft mail of the index.')
            exit(1)

    write_send_mail(draft_mail, args.subject, args.in_reply_to, args.to,
                    args.cc, args.body, args.attach, args.format_only)

def add_common_arguments(parser):
    parser.add_argument('--attach', metavar='<file>', nargs='+',
                        help='file to paste at the end of the body')
    parser.add_argument('--format_only', action='store_true',
            help='print formatted mail template only')

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
    parser.add_argument('--draft', metavar='<index>', type=int,
                        help='resume writing from the given draft')
    add_common_arguments(parser)
