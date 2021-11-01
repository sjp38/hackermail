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

expected inputs are for example:

[0000] 10/29  + crash_dump-fix-boolreturncocci-warning.patch added to -mm tree () (0+
              msgs)
[0001] 10/29  + crash_dump-remove-duplicate-include-in-crash_dumph.patch added to -mm tree
              () (0+ msgs)
[0002] 10/29  + seq_file-fix-passing-wrong-private-data.patch added to -mm tree () (0+
              msgs)
[0003] 10/29  + mm-damon-remove-return-value-from-before_terminate-callback.patch added to
              -mm tree () (0+ msgs)
[0004] 10/29  + scripts-gdb-handle-split-debug-for-vmlinux.patch added to -mm tree () (0+
              msgs)
'''

class MmCommits:
    date = None
    action = None
    patch_title = None

    def __init__(self, date, action, patch_title):
        self.date = date
        self.action = action
        self.patch_title = patch_title

def parse_mails(msg, print_each):
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
    removed = []
    actions = {}
    for mail in mails:
        tokens = mail.split()
        if len(tokens) < 2:
            continue
        date = tokens[1]
        tokens = tokens[2:]
        if len(tokens) < 9:
            continue
        tag = tokens[0]
        patch = tokens[1].split('.patch')[0]
        action = ' '.join(tokens[2:6])
        if tag == '+' and action == 'added to -mm tree':
            if print_each:
                print(mail)
            added.append(MmCommits(date, 'added', patch))
            actions['added'] = True
        if action == 'removed from -mm tree':
            if print_each:
                print(mail)
            removed.append(MmCommits(date, tag, patch))
            actions[tag] = True
    return added, removed, actions

def pr_parsed_changes(added, removed, actions):
    print('added patches')
    print('-------------')
    print()
    for commit in added:
        print(commit.patch_title)

    print()
    print('removed patches')
    print('---------------')
    print()
    for action in actions:
        commits = [x for x in removed if x.action == action]
        for commit in commits:
            print('%s %s' % (commit.action, commit.patch_title))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in_time', action='store_true',
            help='Print mm patch insertion/deletion in time line')
    args = parser.parse_args()

    added, removed, actions = parse_mails(sys.stdin.read(), args.in_time)

    if not args.in_time:
        pr_parsed_changes(added, removed, actions)

    print()
    print('%d added, %d removed' % (len(added), len(removed)))

if __name__ == '__main__':
    main()
