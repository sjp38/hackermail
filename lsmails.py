#!/usr/bin/env python3

import argparse
import datetime
import subprocess

INDENT = ' ' * 4

parser = argparse.ArgumentParser()
parser.add_argument('--since', metavar='since', type=str,
        help='Show mails more recent than a specific date.')
parser.add_argument('--tags', metavar='tag', type=str, nargs='+',
        help='Show mails having the tags (e.g., patch, rfc, ...) only.')
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
    is_reply = False
    orig_subject = None
    tags = []

    def __init__(self, gitid, date, subject_fields):
        self.gitid = gitid
        self.date = date
        self.subject_fields = subject_fields
        self.subject = ' '.join(self.subject_fields)

        if self.subject_fields[0] in ['re:', 'RE:', 'Re:']:
            self.is_reply = True
            self.orig_subject = ' '.join(self.subject_fields[1:])

        if self.subject[0] == '[':
            tag = self.subject[1:].split(']')[0].strip().lower()
            self.tags = tag.split()

duplicate_re_map = {}
to_print = []
for line in subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode(
        'utf-8').strip().split('\n'):
    fields = line.split()
    if len(fields) < 3:
        continue
    mail = Mail(fields[0], fields[1], fields[2:])
    indent = ""

    if filters:
        has_tag = False
        for tag in filters:
            if tag in mail.tags:
                has_tag = True
                break
        if has_tag:
            continue
    if tags:
        has_tag = False
        for tag in tags:
            if tag in mail.tags:
                has_tag = True
                break
        if not has_tag:
            continue

    if mail.is_reply:
        if mail.orig_subject in duplicate_re_map:
            continue
        duplicate_re_map[mail.orig_subject] = True
        indent = INDENT

    if len(mail.tags):
        series = mail.tags[-1].split('/')[0]
        if series.isdigit() and int(series) != 0:
            indent = INDENT

    # date: 2019-09-30T09:57:38+08:00
    date = '/'.join(mail.date.split('T')[0].split('-')[1:])
    to_print.append("%s %s %s%s" % (date, mail.gitid, indent, mail.subject))

for line in reversed(to_print):
    print(line)
