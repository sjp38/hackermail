#!/usr/bin/env python3

import argparse
import subprocess
import sys

import _hkml

def format_reply(mail):
    subject = mail.get_mbox_parsed('subject')
    if subject:
        print("Subject: Re: %s" % subject)
    msgid = mail.get_mbox_parsed('message-id')
    if msgid:
        print("In-Reply-To: %s" % msgid)
    cc = mail.get_mbox_parsed('to')
    if cc:
        print("Cc: %s" % cc)
    cc = mail.get_mbox_parsed('cc')
    if cc:
        print("Cc: %s" % cc)
    from_ = mail.get_mbox_parsed('from')
    if from_:
        print("To: %s" % from_)
    print("")
    date = mail.get_mbox_parsed('date')
    if date and from_:
        print("On %s %s wrote:\n" % (date, from_))
    body = mail.get_mbox_parsed('body')
    for line in body.split('\n'):
        print("> %s" % line)

def set_argparser(parser=None):
    _hkml.set_mail_search_options(parser)
    parser.add_argument('--mbox_file', metavar='mboxfile', type=str,
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

    if args.manifest and args.mlist:
        mails_to_show, threads = _hkml.filter_mails(args)
        format_reply(mails_to_show[0])
        exit(0)

    format_reply(_hkml.Mail.from_mbox(sys.stdin.read()))

if __name__ == '__main__':
    main()
