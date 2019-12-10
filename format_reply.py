#!/usr/bin/env python3

import argparse
import datetime
import subprocess

import _hckmail

def format_reply(mail):
    head_fields = mail.mbox_parsed['header']
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
    for line in mail.mbox_parsed['body'].split('\n'):
        print("> %s" % line)

def set_argparser(parser=None):
    DEFAULT_SINCE = datetime.datetime.now() - datetime.timedelta(days=3)
    DEFAULT_SINCE = "%s-%s-%s" % (DEFAULT_SINCE.year, DEFAULT_SINCE.month,
                DEFAULT_SINCE.day)

    parser.add_argument('--manifest', metavar='manifest', type=str,
            default=_hckmail.DEFAULT_MANIFEST,
            help='Manifesto file in grok\'s format plus site field.')
    parser.add_argument('mlist', metavar='mailing list', type=str,
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

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

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

    format_reply(mails_to_show[0])

if __name__ == '__main__':
    main()
