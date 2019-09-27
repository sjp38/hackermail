#!/usr/bin/env python3

import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('since', metavar='since', type=str, nargs=1,
        help='Show mails more recent than a specific date.')
args = parser.parse_args()
since = args.since

cmd = ("git log --reverse".split() +
        ['--date=iso-strict', '--pretty=%h %ad %s', "--since=%s" % since])

for line in subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode(
        'utf-8').strip().split('\n'):
    fields = line.split()
    gitid = fields[0]
    date = fields[1]
    subject = ' '.join(fields[2:])

    print("%s\t%s\t%s" % (gitid, date, subject))
