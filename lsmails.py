#!/usr/bin/env python3

import argparse
import datetime
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--since', metavar='since', type=str,
        help='Show mails more recent than a specific date.')
parser.add_argument('--tags', metavar='tag', type=str, nargs='+',
        help='Show mails having the tags (e.g., patch, rfc, reply, ...) only.')
parser.add_argument('--filters', metavar='tag', type=str, nargs='+',
        help='Filter out mails having the tags.')

parser.add_argument('--mdir', metavar='mdir', type=str,
        help='Directory containing the mail data.')
args = parser.parse_args()
since = args.since
tags = args.tags
filters = args.filters
mdir = args.mdir

if not since:
    since_date = datetime.datetime.now() - datetime.timedelta(days=3)
    since = "%s-%s-%s" % (since_date.year, since_date.month, since_date.day)

if not mdir:
    mdir = "./.git"

cmd = ["git", "--git-dir=%s" % mdir, "log",
        '--date=iso-strict', '--pretty=%h %ad %s', "--since=%s" % since]

class Mail:
    gitid = None
    date = None
    subject_fields = None
    subject = None
    orig_subject = None
    tags = None
    series = None

    def __init__(self, gitid, date, subject_fields):
        self.gitid = gitid
        self.date = date
        self.subject_fields = subject_fields
        self.subject = ' '.join(self.subject_fields)
        self.tags = []

        if self.subject_fields[0].lower() == 're:':
            self.tags.append('reply')
            self.orig_subject = ' '.join(self.subject_fields[1:])
            return

        if self.subject[0] == '[':
            tag = self.subject[1:].split(']')[0].strip().lower()
            self.tags = tag.split()

            series = self.tags[-1].split('/')
            if series[0].isdigit() and series[1].isdigit():
                self.series = [int(x) for x in series]

def valid_to_show(mail):
    has_tag = False
    if filters:
        for tag in filters:
            if tag in mail.tags:
                has_tag = True
                break
        if has_tag:
            return False

    if tags:
        for tag in tags:
            if tag in mail.tags:
                has_tag = True
                break
        if not has_tag:
            return False
    return True

mails_to_show = []
duplicate_re_map = {}
for line in subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode(
        'utf-8').strip().split('\n'):
    fields = line.split()
    if len(fields) < 3:
        continue
    mail = Mail(fields[0], fields[1], fields[2:])

    if not valid_to_show(mail):
        continue

    # Shows only latest reply for given mail
    if mail.tags and 'reply' in mail.tags:
        if mail.orig_subject in duplicate_re_map:
            continue
        duplicate_re_map[mail.orig_subject] = True

    mails_to_show.append(mail)

for mail in reversed(mails_to_show):
    indent = ""
    if (mail.series and mail.series[0] > 0) or ('reply' in mail.tags):
        indent = "    "

    # date: 2019-09-30T09:57:38+08:00
    date = '/'.join(mail.date.split('T')[0].split('-')[1:])
    print("%s %s %s%s" % (date, mail.gitid, indent, mail.subject))
