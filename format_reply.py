#!/usr/bin/env python3

import argparse
import subprocess
import sys

import _hkml
import format_mail

def format_reply(mail):
    subject = mail.get_field('subject')
    if subject and subject.split()[0].lower() != 're:':
        subject = 'Re: %s' % subject

    in_reply_to = mail.get_field('message-id')
    cc = [x for x in [mail.get_field('to'), mail.get_field('cc')] if x]
    to = [mail.get_field('from')]

    body_lines = []
    date = mail.get_field('date')
    if date and to[0]:
        body_lines.append('On %s %s wrote:' % (date, to[0]))
        body_lines.append('')
    body = mail.get_field('body')
    for line in body.split('\n'):
        body_lines.append('> %s' % line)
    body = '\n'.join(body_lines)

    return format_mail.format_mbox(subject, in_reply_to, to, cc, body)

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
