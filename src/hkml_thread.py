#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

import _hkml
import _hkml_list_cache
import hkml_cache
import hkml_list


def thread_str(mail_id, dont_use_internet, show_url):
    if mail_id.isdigit():
        mail_id = int(mail_id)
        msgid = None
    else:
        msgid = mail_id

    mails_to_show = None
    if dont_use_internet is False:
        if msgid is None:
            mail = _hkml_list_cache.get_mail(mail_id, not_thread_idx=True)
            if mail is None:
                print("wrong <mail_id>")
                exit(1)
            msgid = mail.get_field("message-id")

        mails_to_show, err = hkml_list.get_thread_mails_from_web(msgid)
        if err is not None:
            print(err)
        else:
            mail_id = None
    if mails_to_show is None:
        mails_to_show = _hkml_list_cache.last_listed_mails()
        # TODO: Support msgid

    nr_cols_in_line = int(os.get_terminal_size().columns * 9 / 10)
    list_decorator = hkml_list.MailListDecorator(None)
    list_decorator.show_stat = False
    list_decorator.ascend = (True,)
    list_decorator.sort_threads_by = (["first_date"],)
    list_decorator.collapse = False
    list_decorator.show_url = show_url
    list_decorator.cols = nr_cols_in_line
    list_decorator.show_runtime_profile = False

    list_data, err = hkml_list.mails_to_list_data(
        mails_to_show,
        do_find_ancestors_from_cache=False,
        mails_filter=None,
        list_decorator=list_decorator,
        show_thread_of=mail_id,
        runtime_profile=[],
        stat_only=False,
        stat_authors=False,
    )
    if err is not None:
        print("mails_to_list_data() fail (%s)" % err)
        exit(1)
    return list_data


def main(args):
    if args.mail_id is None:
        cached = _hkml_list_cache.get_last_thread()
        if cached is None:
            print("No message identifier or cached thread")
            return
        to_show, mail_idx_key_map = cached
        _hkml_list_cache.writeback_list_output()
        hkml_list.show_list(
            to_show,
            to_stdout=False,
            to_less=args.no_interactive,
            mail_idx_key_map=mail_idx_key_map,
        )
        return

    list_data = thread_str(args.mail_id, args.dont_use_internet, args.url)
    to_show = list_data.text
    mail_idx_key_map = list_data.mail_idx_key_map
    if args.dont_use_internet is False:
        hkml_cache.writeback_mails()
        _hkml_list_cache.set_item("thread_output", list_data)
    hkml_list.show_list(
        to_show,
        to_stdout=False,
        to_less=args.no_interactive,
        mail_idx_key_map=mail_idx_key_map,
    )


def set_argparser(parser=None):
    parser.description = "list mails of a thread"
    _hkml.set_manifest_option(parser)
    parser.add_argument(
        "mail_id",
        metavar="<mail identifier>",
        nargs="?",
        help=" ".join(
            [
                "Identifier of any mail in the thread to list.",
                "Could be the index on the last-generated list or thread,",
                "or the Message-ID of the mail.",
                "If this is not given, shows last thread output.",
            ]
        ),
    )
    parser.add_argument("--url", action="store_true", help="print URLs for mails")
    parser.add_argument(
        "--dont_use_internet",
        action="store_true",
        help="don't use internet do get the mails",
    )
    parser.add_argument(
        "--no_interactive",
        action="store_true",
        help="don't use hkml interactive list viewer",
    )
