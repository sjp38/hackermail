#!/usr/bin/env python3

import argparse
import datetime
import subprocess
import sys

import _hckmail

def format_reply(mbox_parsed):
    head_fields = mbox_parsed['header']
    if 'subject' in head_fields:
        print("Subject: Re: %s" % head_fields['subject'])
    if 'message-id' in head_fields:
        print("In-Reply-To: %s" % head_fields['message-id'])
    if 'cc' in head_fields:
        print("Cc: %s" % head_fields['cc'])
    if 'from' in head_fields:
        print("To: %s" % head_fields['from'])
    print("")
    print("On %s %s wrote:\n" % (head_fields['date'], head_fields['from']))
    for line in mbox_parsed['body'].split('\n'):
        print("> %s" % line)

def set_argparser(parser=None):
    DEFAULT_SINCE = datetime.datetime.now() - datetime.timedelta(days=3)
    DEFAULT_SINCE = "%s-%s-%s" % (DEFAULT_SINCE.year, DEFAULT_SINCE.month,
                DEFAULT_SINCE.day)

    parser.add_argument('--manifest', metavar='manifest', type=str,
            default=_hckmail.DEFAULT_MANIFEST,
            help='Manifesto file in grok\'s format plus site field.')
    parser.add_argument('mlist', metavar='mailing list', type=str, nargs='?',
            help='Mailing list to show.')
    parser.add_argument('--since', metavar='since', type=str,
            default=DEFAULT_SINCE,
            help='Show mails more recent than a specific date.')
    parser.add_argument('--show', metavar='tags', type=str,
            help='Tags seperated by comma.  Show mails having the tags.')
    parser.add_argument('--hide', metavar='tag', type=str,
            help='Tags seperated by comma.  Hide mails having the tags.')
    parser.add_argument('--msgid', metavar='msgid', type=str,
            help='Message Id of the mail to show.')
    parser.add_argument('index', metavar='idx', type=int, nargs='?',
            help='Index of the mail to format reply for.')
    parser.add_argument('--mbox_file', metavar='mboxfile', type=str,
            help='Mbox format file of the mail to format reply for.')
    parser.add_argument('--stdin', action='store_true',
            help='Mbox format content is received via stdin.')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.stdin:
        parsed = _hckmail.parse_mbox(sys.stdin.read())
        format_reply(parsed)
        exit(0)

    if args.mbox_file:
        with open(args.mbox_file, 'r') as f:
            parsed = _hckmail.parse_mbox(f.read())
            format_reply(parsed)
        exit(0)

    manifest_file = args.manifest
    mail_list = args.mlist
    since = args.since

    tags_to_show = []
    tags_to_hide = []
    if args.show:
        tags_to_show = args.show.split(',')
    if args.hide:
        tags_to_hide = args.hide.split(',')
    msgid = args.msgid

    idx_of_mail = args.index

    manifest = _hckmail.get_manifest(manifest_file)
    if not manifest:
        print("Cannot open manifest file %s" % manifest_file)
        parser.print_help()
        exit(1)

    mails_to_show, threads = _hckmail.filter_mails(manifest, mail_list, since,
            tags_to_show, tags_to_hide, msgid, idx_of_mail)

    format_reply(mails_to_show[0].mbox_parsed)

if __name__ == '__main__':
    main()
