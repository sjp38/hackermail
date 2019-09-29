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

    def __init__(self, gitid, date, subject_fields):
        self.gitid = gitid
        self.date = date
        self.subject_fields = subject_fields
        self.subject = ' '.join(self.subject_fields)
        if self.subject_fields[0] in ['re:', 'RE:', 'Re:']:
            self.is_reply = True
            self.orig_subject = ' '.join(self.subject_fields[1:])

    def get_tag_fields(self):
        subject = ' '.join(self.subject_fields)
        if subject[0] != '[':
            return None
        tag = subject[1:].split(']')[0].strip()
        return tag.split()

    def is_patch(self):
        tag_fields = self.get_tag_fields()
        if not tag_fields:
            return False
        if tag_fields[0] == 'PATCH':
            return True
        return False

    def is_rfc(self):
        tag_fields = self.get_tag_fields()
        if not tag_fields:
            return False
        if tag_fields[0] == 'RFC':
            return True

duplicate_re_map = {}
to_print = []
for line in subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode(
        'utf-8').strip().split('\n'):
    fields = line.split()

    gitid = fields[0]
    date = fields[1]
    subject_fields = fields[2:]
    subject = ' '.join(fields[2:])
    mail = Mail(fields[0], fields[1], fields[2:])

    if mail.is_reply:
        if not 'etc' in types:
            continue
        if mail.orig_subject in duplicate_re_map:
            continue
        duplicate_re_map[mail.orig_subject] = True
        subject = INDENT + mail.subject

    if mail.is_patch() and not 'patch' in types:
        continue
    if mail.is_rfc() and not 'rfc' in types:
        continue
    if mail.is_patch() or mail.is_rfc():
        tag = subject[1:].split(']')[0].strip()
        tag_fields = tag.split()
        series = tag_fields[-1].split('/')[0]
        if series.isdigit() and int(series) != 0:
            subject = INDENT + subject
    elif not 'etc' in types:
            continue

    to_print.append("%s [%s] %s" % (gitid, date, subject))

for line in reversed(to_print):
    print(line)
