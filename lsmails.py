#!/usr/bin/env python3

import argparse
import datetime
import subprocess

INDENT = ' ' * 4

parser = argparse.ArgumentParser()
parser.add_argument('--since', metavar='since', type=str,
        help='Show mails more recent than a specific date.')
parser.add_argument('--types', metavar='types', type=str, nargs='+',
        help='Type of mails (patch, rfc, etc, all) to show.')
parser.add_argument('--mdir', metavar='mdir', type=str,
        help='Directory containing the mail data.')
args = parser.parse_args()
since = args.since
types = args.types
mdir = args.mdir

if not since:
    since_date = datetime.datetime.now() - datetime.timedelta(days=3)
    since = "%s-%s-%s" % (since_date.year, since_date.month, since_date.day)

if not types or 'all' in types:
    types = ['patch', 'rfc', 'etc']

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
    is_patch = False
    is_rfc = False
    patch_tag_fields = None

    def __init__(self, gitid, date, subject_fields):
        self.gitid = gitid
        self.date = date
        self.subject_fields = subject_fields
        self.subject = ' '.join(self.subject_fields)

        if self.subject_fields[0] in ['re:', 'RE:', 'Re:']:
            self.is_reply = True
            self.orig_subject = ' '.join(self.subject_fields[1:])

        if self.subject[0] == '[':
            tag = self.subject[1:].split(']')[0].strip()
            self.patch_tag_fields = tag.split()
            if len(self.patch_tag_fields) == 0:
                return
            if 'PATCH' in [x.upper() for x in self.patch_tag_fields]:
                self.is_patch = True
            if 'RFC' in [x.upper() for x in self.patch_tag_fields]:
                self.is_patch = True
                self.is_rfc = True

duplicate_re_map = {}
to_print = []
for line in subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode(
        'utf-8').strip().split('\n'):
    fields = line.split()
    if len(fields) < 3:
        continue
    mail = Mail(fields[0], fields[1], fields[2:])
    indent = ""

    if mail.is_patch:
        # TODO: [PATCHSET] [RESEND], etc
        if not mail.is_rfc and not 'patch' in types:
            continue
        if mail.is_rfc and not 'rfc' in types:
            continue
        series = mail.patch_tag_fields[-1].split('/')[0]
        if series.isdigit() and int(series) != 0:
            indent = INDENT
    else:
        if not 'etc' in types:
            continue
        if mail.is_reply:
            if mail.orig_subject in duplicate_re_map:
                continue
            duplicate_re_map[mail.orig_subject] = True
            indent = INDENT

    # date: 2019-09-30T09:57:38+08:00
    date = '/'.join(mail.date.split('T')[0].split('-')[1:])
    to_print.append("%s %s %s%s" % (date, mail.gitid, indent, mail.subject))

for line in reversed(to_print):
    print(line)
