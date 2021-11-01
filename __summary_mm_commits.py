#!/usr/bin/env python3

import argparse
import sys

'''
mails to parse

incoming
mmotm 2021-10-05-19-53 uploaded
+ mm-damon-dbgfs-support-physical-memory-monitoring.patch added to -mm tree
[to-be-updated] aa-bbb-ccc-blah.patch removed from -mm tree
[obsolete] aaa.patch removed from -mm tree
[withdrawn] blah-blah.patch removed from -mm tree
[nacked] memblock-neaten-logging.patch removed from -mm tree
[folded-merged] aa-bb-cc.patch removed from -mm tree
[merged] aa-bb-cc.patch removed from -mm tree
'''

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in_time', action='store_true',
            help='Print mm patch insertion/deletion in time line')
    args = parser.parse_args()

    msg = sys.stdin.read()
    mails = []
    mail = ''
    for line in msg.split('\n'):
        if not line.startswith(' '):
            if mail != '':
                mails.append(mail)
            mail = ''
        mail = ' '.join([mail, line.strip()])
    if mail != '':
        mails.append(mail)

    added = []
    removed = {}
    for mail in mails:
        tokens = mail.split()[2:]
        if len(tokens) < 9:
            continue
        tag = tokens[0]
        patch = tokens[1].split('.patch')[0]
        action = ' '.join(tokens[2:6])
        if tag == '+' and action == 'added to -mm tree':
            if args.in_time:
                print(mail)
            added.append(patch)
        if action == 'removed from -mm tree':
            if args.in_time:
                print(mail)
            if not tag in removed:
                removed[tag] = []
            removed[tag].append(patch)

    if not args.in_time:
        print('added patches')
        print('-------------')
        print()
        for patch in added:
            print(patch)

        print()
        print('removed patches')
        print('---------------')
        print()
        for tag in removed:
            for patch in removed[tag]:
                print('%s %s' % (tag, patch))

    nr_removes = 0
    for tag in removed:
        nr_removes += len(removed[tag])
    print()
    print('%d added, %d removed' % (len(added), nr_removes))

if __name__ == '__main__':
    main()
