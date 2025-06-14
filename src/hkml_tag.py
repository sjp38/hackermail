# SPDX-License-Identifier: GPL-2.0

import json
import os
import sys

import _hkml
import _hkml_list_cache
import hkml_sync

"""
Tags information is saved in a json file called 'tags' under the hkml
directory.

The data structure is a map.  Keys are msgid of mails.  Values are map having
keys 'mail' and 'tags'.  'mail' is _hkml.Mail.to_kvpairs() output of the mail
of the message id.  'tags' is a list of tags for the mail.
"""


def tag_file_path():
    return os.path.join(_hkml.get_hkml_dir(), "tags")


def read_tags_file():
    tags_map = {}
    for filename in os.listdir(_hkml.get_hkml_dir()):
        if not filename.startswith("tags"):
            continue
        with open(os.path.join(_hkml.get_hkml_dir(), filename), "r") as f:
            for k, v in json.load(f).items():
                tags_map[k] = v
    return tags_map


def write_tags_single_file(tags_map, file_idx):
    if file_idx is not None:
        suffix = "_%d" % file_idx
    else:
        suffix = ""
    file_path = os.path.join(_hkml.get_hkml_dir(), "tags%s" % suffix)
    with open(file_path, "w") as f:
        json.dump(tags_map, f, indent=4, sort_keys=True)


def write_tags_file(tags_map, sync_after):
    max_mails_per_file = 100
    tags_map_to_write = {}
    file_idx = 0
    for msgid in sorted(tags_map.keys()):
        tags_map_to_write[msgid] = tags_map[msgid]
        if len(tags_map_to_write) == max_mails_per_file:
            write_tags_single_file(tags_map_to_write, file_idx)
            tags_map_to_write = {}
            file_idx += 1
    write_tags_single_file(tags_map_to_write, None)

    if hkml_sync.syncup_ready() and sync_after is True:
        hkml_sync.syncup(_hkml.get_hkml_dir(), remote=None)


class TagChange:
    mail = None
    add = None
    remove = None

    def __init__(self, mail, add=False, remove=False):
        self.mail = mail
        self.add = add
        self.remove = remove


def mails_of_tag(tag):
    tags_map = read_tags_file()
    mails = []
    for msgid in tags_map:
        tags = tags_map[msgid]["tags"]
        if tag in tags:
            mails.append(_hkml.Mail(kvpairs=tags_map[msgid]["mail"]))
    return mails


def ask_sync_before_change():
    if hkml_sync.syncup_ready():
        answer = input("Gonna read/write tags.  Sync before and after? [Y/n] ")
        if answer.lower() != "n":
            hkml_sync.syncup(_hkml.get_hkml_dir(), remote=None)
            return True
    return False


def get_mails_of_subject_tag(subject, tag):
    mails = []
    tags_map = read_tags_file()
    for msgid in tags_map:
        tags = tags_map[msgid]["tags"]
        if not tag in tags:
            continue
        mail = _hkml.Mail(kvpairs=tags_map[msgid]["mail"])
        if mail.subject == subject:
            mails.append(mail)
    return mails


def suggest_removing_drafts_of_subject(subject, tags_map):
    for msgid in tags_map:
        tags = tags_map[msgid]["tags"]
        if not "drafts" in tags:
            continue
        draft_mail = _hkml.Mail(kvpairs=tags_map[msgid]["mail"])
        if draft_mail.subject != subject:
            continue
        while True:
            prompt = 'remove draft of subject "%s" that written on %s? [y/n] ' % (
                subject,
                draft_mail.date,
            )
            answer = input(prompt)
            if answer.lower() not in ["y", "n"]:
                continue
            if answer.lower() == "y":
                tags.remove("drafts")
            break


def add_tags_to_map(mail, tags, tags_map):
    msgid = mail.get_field("message-id")

    if not msgid in tags_map:
        tags_map[msgid] = {"mail": mail.to_kvpairs(), "tags": tags}
    else:
        existing_tags = tags_map[msgid]["tags"]
        for tag in tags:
            if not tag in existing_tags:
                existing_tags.append(tag)


def do_add_tags(mail, tags, draft_subject=None):
    sync_after = ask_sync_before_change()

    tags_map = read_tags_file()

    if "drafts" in tags or "sent" in tags:
        if draft_subject is None:
            draft_subject = mail.subject
        suggest_removing_drafts_of_subject(draft_subject, tags_map)

    add_tags_to_map(mail, tags, tags_map)
    write_tags_file(tags_map, sync_after)


def add_tags(mail_idx, tags):
    mail = _hkml_list_cache.get_mail(mail_idx)
    if mail is None:
        print("failed getting mail of the index.  Maybe wrong index?")
        exit(1)

    do_add_tags(mail, tags, None)


def do_remove_tags(mail, tags):
    msgid = mail.get_field("message-id")

    sync_after = ask_sync_before_change()
    tags_map = read_tags_file()
    if not msgid in tags_map:
        print("seems the index is wrong, or having no tag")
        exit(1)
    existing_tags = tags_map[msgid]["tags"]
    for tag in tags:
        if not tag in existing_tags:
            print("the mail is not having the tag")
            exit(1)
        existing_tags.remove(tag)
    write_tags_file(tags_map, sync_after)


def remove_tags(mail_idx, tags):
    mail = _hkml_list_cache.get_mail(mail_idx)
    if mail is None:
        print("failed getting mail of the index.  Maybe wrong index?")
        exit(1)

    do_remove_tags(mail, tags)


def get_tag_nr_mails():
    """
    Return dict having tags as key, numbers of mails of the tag as value
    """
    tag_nr_mails = {}
    tags_map = read_tags_file()
    for msgid in tags_map:
        for tag in tags_map[msgid]["tags"]:
            if not tag in tag_nr_mails:
                tag_nr_mails[tag] = 0
            tag_nr_mails[tag] += 1
    return tag_nr_mails


def tag_exists(tagname):
    return tagname in get_tag_nr_mails()


def list_tags():
    tag_nr_mails = get_tag_nr_mails()
    for tag in sorted(tag_nr_mails.keys()):
        print("%s: %d mails" % (tag, tag_nr_mails[tag]))


def main(args):
    if args.action == "add":
        return add_tags(args.mail_idx, args.tags)
    elif args.action == "remove":
        if args.mail_idx is None and len(args.mails) == 0:
            print("mail to remove tags are not specified")
            exit(1)
        if args.mail_idx is not None:
            args.mails.append(args.mail_idx)
        for mail_idx in args.mails:
            remove_tags(mail_idx, args.tags)
        return
    elif args.action == "list":
        return list_tags()


def set_argparser(parser):
    parser.description = "manage tags of mails"
    if sys.version_info >= (3, 7):
        subparsers = parser.add_subparsers(
            title="action", dest="action", metavar="<action>", required=True
        )
    else:
        subparsers = parser.add_subparsers(
            title="action", dest="action", metavar="<action>"
        )

    parser_add = subparsers.add_parser("add", help="add tags to a mail")
    parser_add.add_argument(
        "mail_idx", metavar="<index>", type=int, help="index of the mail to add tags"
    )
    parser_add.add_argument(
        "tags", metavar="<string>", nargs="+", help="tags to add to the mail"
    )

    parser_remove = subparsers.add_parser("remove", help="remove tags from a mail")
    parser_remove.add_argument(
        "mail_idx",
        metavar="<index>",
        type=int,
        nargs="?",
        help="index of the mail to remove tags",
    )
    parser_remove.add_argument(
        "tags", metavar="<string>", nargs="+", help="tags to remove from the mail"
    )
    parser_remove.add_argument(
        "--mails",
        metavar="<index>",
        type=int,
        nargs="+",
        default=[],
        help="indexes of the mails to remove tags",
    )

    parser_list = subparsers.add_parser("list", help="list tags")


def handle_may_sent_mail(mail, sent, orig_draft_subject):
    """Handle tags of a mail that may sent or not"""

    sync_after = ask_sync_before_change()

    # suggest tagging the may or may not sent mail
    if sent:
        tag_name = "sent"
    else:
        tag_name = "drafts"
    answer = input("Tag the mail (%s) as %s? [Y/n] " % (mail.subject, tag_name))
    tag_may_sent_mail = answer.lower() != "n"

    tags_map = read_tags_file()

    # regardless of the answer to the above question, suggest removing
    # drafts
    if orig_draft_subject is None:
        orig_draft_subject = mail.subject
    suggest_removing_drafts_of_subject(orig_draft_subject, tags_map)

    # do the tagging of the mail.  Do this after the above duplicate drafts
    # removing, since otherwise this mail may tagged as draft and the duplicate
    # draft removing may find it as the draft.
    if tag_may_sent_mail:
        add_tags_to_map(mail, [tag_name], tags_map)

    write_tags_file(tags_map, sync_after)
