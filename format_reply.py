#!/usr/bin/env python3

import argparse
import subprocess
import sys

import _hkml

def format_reply(mbox_parsed):
    subject = _hkml.get_mbox_field(mbox_parsed, 'subject')
    if subject:
        print("Subject: Re: %s" % subject)
    msgid = _hkml.get_mbox_field(mbox_parsed, 'message-id')
    if msgid:
        print("In-Reply-To: %s" % msgid)
    cc = _hkml.get_mbox_field(mbox_parsed, 'to')
    if cc:
        print("Cc: %s" % cc)
    cc = _hkml.get_mbox_field(mbox_parsed, 'cc')
    if cc:
        print("Cc: %s" % cc)
    from_ = _hkml.get_mbox_field(mbox_parsed, 'from')
    if from_:
        print("To: %s" % from_)
    print("")
    date = _hkml.get_mbox_field(mbox_parsed, 'date')
    if date and from_:
        print("On %s %s wrote:\n" % (date, from_))
    body = _hkml.get_mbox_field(mbox_parsed, 'body')
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
            format_reply(_hkml.Mail(f.read()).get_mbox_parsed_field())
        exit(0)

    if args.manifest and args.mlist:
        mails_to_show, threads = _hkml.filter_mails(args)
        format_reply(mails_to_show[0].get_mbox_parsed_field())
        exit(0)

    format_reply(_hkml.Mail(sys.stdin.read()).get_mbox_parsed_field())

if __name__ == '__main__':
    main()
