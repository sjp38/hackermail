#!/usr/bin/env python3

import argparse
import subprocess

INDENT = ' ' * 4

parser = argparse.ArgumentParser()
parser.add_argument('since', metavar='since', type=str, nargs=1,
        help='Show mails more recent than a specific date.')
parser.add_argument('--types', metavar='types', type=str, nargs='+',
        help='Type of mails (patch, rfc, etc, all) to show.')
args = parser.parse_args()
since = args.since
types = args.types

if not types or 'all' in types:
    types = ['patch', 'rfc', 'etc']

cmd = ("git log".split() +
        ['--date=iso-strict', '--pretty=%h %ad %s', "--since=%s" % since])

class Mail:
    gitid = None
    date = None
    subject_fields = None
    subject = None
    is_reply = False
    orig_subject = None
    is_patch = False
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
            if len(self.patch_tag_fields) > 0:
                self.is_patch = True

duplicate_re_map = {}
to_print = []
for line in subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode(
        'utf-8').strip().split('\n'):
    fields = line.split()
    mail = Mail(fields[0], fields[1], fields[2:])
    indent = ""

    if mail.is_reply:
        if not 'etc' in types:
            continue
        if mail.orig_subject in duplicate_re_map:
            continue
        duplicate_re_map[mail.orig_subject] = True
        indent = INDENT

    if mail.is_patch and mail.patch_tag_fields[0] == 'PATCH' and not 'patch' in types:
        continue
    if mail.is_patch and mail.patch_tag_fields[0] == 'RFC' and not 'rfc' in types:
        continue
    if mail.is_patch:
        series = mail.patch_tag_fields[-1].split('/')[0]
        if series.isdigit() and int(series) != 0:
            indent = INDENT
    elif not 'etc' in types:
            continue

    to_print.append("%s [%s] %s%s" % (mail.gitid, mail.date, indent, mail.subject))

for line in reversed(to_print):
    print(line)
