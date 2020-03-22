#!/usr/bin/env python3

import argparse
import subprocess
import sys

import _hkml

def format_reply(mail):
    subject = mail.get_field('subject')
    if subject:
        print("Subject: Re: %s" % subject)
    msgid = mail.get_field('message-id')
    if msgid:
        print("In-Reply-To: %s" % msgid)
    cc = mail.get_field('to')
    if cc:
        print("Cc: %s" % cc)
    cc = mail.get_field('cc')
    if cc:
        print("Cc: %s" % cc)
    from_ = mail.get_field('from')
    if from_:
        print("To: %s" % from_)
    print("")
    date = mail.get_field('date')
    if date and from_:
        print("On %s %s wrote:\n" % (date, from_))
    body = mail.get_field('body')
    for line in body.split('\n'):
        print("> %s" % line)

def set_argparser(parser=None):
    parser.add_argument('mbox_file', metavar='mboxfile', type=str, nargs='?',
            help='Mbox format file of the mail to format reply for.')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.mbox_file:
        with open(args.mbox_file, 'r') as f:
            format_reply(_hkml.Mail.from_mbox(f.read()))
        exit(0)

    format_reply(_hkml.Mail.from_mbox(sys.stdin.read()))

if __name__ == '__main__':
    main()
