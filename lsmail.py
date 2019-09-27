#!/usr/bin/env python3

import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('since', metavar='since', type=str, nargs=1,
        help='Show mails more recent than a specific date.')
args = parser.parse_args()
since = args.since

cmd = ("git log".split() +
        ['--date=iso-strict', '--pretty=%h %ad %s', "--since=%s" % since])

duplicate_re_map = {}

for line in subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode(
        'utf-8').strip().split('\n'):
    fields = line.split()
    gitid = fields[0]
    date = fields[1]
    subject_fields = fields[2:]
    subject = ' '.join(fields[2:])

    is_reply = False
    if subject_fields[0] in ['re:', 'RE:', 'Re:']:
        is_reply = True
        original_subject = ' '.join(subject_fields[1:])
        if original_subject in duplicate_re_map:
            continue
        subject = '\t' + subject
        duplicate_re_map[original_subject] = True

    if subject[0] == '[':
        tag = subject[1:].split(']')[0].strip()
        tag_fields = tag.split()
        if tag_fields[0] in ['PATCH', 'RFC']:
            series = tag_fields[-1].split('/')[0]
            if series.isdigit() and int(series) != 0:
                subject = '\t' + subject

    print("%s\t%s\t%s" % (gitid, date, subject))
