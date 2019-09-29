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

duplicate_re_map = {}

to_print = []

for line in subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode(
        'utf-8').strip().split('\n'):
    fields = line.split()
    gitid = fields[0]
    date = fields[1]
    subject_fields = fields[2:]
    subject = ' '.join(fields[2:])

    if subject_fields[0] in ['re:', 'RE:', 'Re:']:
        if not 'etc' in types:
            continue
        original_subject = ' '.join(subject_fields[1:])
        if original_subject in duplicate_re_map:
            continue
        subject = INDENT + subject
        duplicate_re_map[original_subject] = True

    if subject[0] == '[':
        tag = subject[1:].split(']')[0].strip()
        tag_fields = tag.split()
        if tag_fields[0] in ['PATCH', 'RFC']:
            if tag_fields[0] == 'PATCH' and not 'patch' in types:
                continue
            if tag_fields[0] == 'RFC' and not 'rfc' in types:
                continue
            series = tag_fields[-1].split('/')[0]
            if series.isdigit() and int(series) != 0:
                subject = INDENT + subject
        elif not 'etc' in types:
            continue

    to_print.append("%s [%s] %s" % (gitid, date, subject))

for line in reversed(to_print):
    print(line)
