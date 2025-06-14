#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import sys

"""
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

[0000] + crash_dump-fix-boolreturncocci-warning.patch added to -mm tree
       (Andrew Morton, 10/29, 0+
              msgs)
[0001] + crash_dump-remove-duplicate-include-in-crash_dumph.patch added to -mm
       tree (Andrew Morton, 10/29, 0+ msgs)
[0002] + seq_file-fix-passing-wrong-private-data.patch added to -mm tree
       (Andrew Morton, 10/29, 0+ msgs)
"""


class MmCommits:
    date = None
    action = None
    from_to = None
    patch_title = None

    def __init__(self, date, action, from_to, patch_title):
        self.date = date
        self.action = action
        self.from_to = from_to
        self.patch_title = patch_title


def parse_mails(msg):
    mails = []
    mail = ""
    for line in msg.split("\n"):
        if not line.startswith("[") and not line.startswith(" "):
            continue
        if not line.startswith(" "):
            if mail != "":
                mails.append(mail)
            mail = ""
        mail = " ".join([mail, line.strip()])
    if mail != "":
        mails.append(mail)

    added = []
    removed = []
    actions = {}
    for mail in mails:
        tokens = mail.split()
        if len(tokens) < 1:
            continue
        date = tokens[-4]
        tokens = tokens[1:]
        if len(tokens) < 9:
            continue
        tag = tokens[0]
        patch = tokens[1].split(".patch")[0]
        action = " ".join(tokens[2:6])
        if tag == "+" and action.startswith("added to "):
            dst_tree = tokens[4]
            added.append(MmCommits(date, "added", dst_tree, patch))
            actions["added"] = True
        if action.startswith("removed from "):
            src_tree = tokens[4]
            removed.append(MmCommits(date, tag, src_tree, patch))
            actions[tag] = True
    return added, removed, actions


def __pr_parsed_changes(added, removed, actions):
    print("added patches")
    print("-------------")
    print()
    for commit in added:
        print("%s (%s)" % (commit.patch_title, commit.from_to))

    print()
    print("removed patches")
    print("---------------")
    print()
    for action in actions:
        commits = [x for x in removed if x.action == action]
        for commit in commits:
            print("%s %s (%s)" % (commit.action, commit.patch_title, commit.from_to))

    print()
    print("%d added, %d removed" % (len(added), len(removed)))


def pr_parsed_changes(added, removed, actions, daily):
    if not daily:
        __pr_parsed_changes(added, removed, actions)
        return

    days = {}
    for commit in added + removed:
        days[commit.date] = True

    for day in sorted(days.keys()):
        print(day)
        print("=" * len(day))
        print()
        daily_added = [x for x in added if x.date == day]
        daily_removed = [x for x in removed if x.date == day]
        daily_actions = {}
        for c in daily_removed:
            daily_actions[c.action] = True
        __pr_parsed_changes(daily_added, daily_removed, daily_actions)
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--total", action="store_true", help="Print in total, not daily"
    )
    args = parser.parse_args()

    added, removed, actions = parse_mails(sys.stdin.read())

    pr_parsed_changes(added, removed, actions, not args.total)


if __name__ == "__main__":
    main()
