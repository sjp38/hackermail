#!/usr/bin/env python3

import argparse
import subprocess
import sys

import _hkml

def git_sendemail_valid_recipients(recipients):
    """each line should be less than 998 char"""
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

def format_reply(mail):
    subject = mail.get_field('subject')
    if subject:
        prefix = 'Subject: '
        if subject.split()[0].lower() != 're':
            prefix += 'Re: '
        print('%s %s' % (prefix, subject))
    msgid = mail.get_field('message-id')
    if msgid:
        print('In-Reply-To: %s' % msgid)
    to = mail.get_field('to')
    if to:
        to = git_sendemail_valid_recipients(to)
        print('Cc: %s' % to)
    cc = mail.get_field('cc')
    if cc:
        cc = git_sendemail_valid_recipients(cc)
        print('Cc: %s' % cc)
    from_ = mail.get_field('from')
    if from_:
        print('To: %s' % from_)
    print('')
    date = mail.get_field('date')
    if date and from_:
        print('On %s %s wrote:\n' % (date, from_))
    body = mail.get_field('body')
    for line in body.split('\n'):
        print('> %s' % line)

def set_argparser(parser=None):
    parser.add_argument('mbox_file', metavar='<file>', type=str, nargs='?',
            help='Mbox format file of the mail to format reply for.')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.mbox_file:
        with open(args.mbox_file, 'r') as f:
            format_reply(_hkml.Mail.from_mbox(f.read()))
        return

    format_reply(_hkml.Mail.from_mbox(sys.stdin.read()))

if __name__ == '__main__':
    main()
