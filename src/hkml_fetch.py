#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import subprocess

import _hkml
import _hkml_list_cache


def fetch_mail(mail_lists, quiet=False, epochs=1):
    site = _hkml.get_manifest()["site"]
    for mlist in mail_lists:
        _hkml_list_cache.invalidate_cached_outputs(mlist)
        repo_paths = _hkml.mail_list_repo_paths(mlist)[:epochs]
        local_paths = _hkml.mail_list_data_paths(mlist)[:epochs]

        for idx, repo_path in enumerate(repo_paths):
            git_url = "%s%s" % (site, repo_path)
            local_path = local_paths[idx]
            if not os.path.isdir(local_path):
                cmd = "git clone --mirror %s %s" % (git_url, local_path)
            else:
                cmd = "git --git-dir=%s remote update" % local_path
            if not quiet:
                print(cmd)
                subprocess.call(cmd.split())
            else:
                with open(os.devnull, "w") as f:
                    subprocess.call(cmd.split(), stdout=f)
    _hkml_list_cache.writeback_list_output_cache()


def fetched_mail_lists():
    archive_dir = os.path.join(_hkml.get_hkml_dir(), "archives")
    return [
        d
        for d in os.listdir(archive_dir)
        if os.path.isdir(os.path.join(archive_dir, d))
    ]


def main(args):
    mail_lists = args.mlist
    if not mail_lists:
        mail_lists = fetched_mail_lists()
    if not mail_lists:
        print("mail lists to fetch is not specified")
        exit(1)
    quiet = args.quiet
    fetch_mail(mail_lists, quiet, args.epochs)


def set_argparser(parser):
    parser.description = "fetch mails"
    _hkml.set_manifest_option(parser)
    parser.add_argument(
        "mlist", metavar="<mailing list>", nargs="*", help="mailing list to fetch."
    )
    parser.add_argument(
        "--quiet", "-q", default=False, action="store_true", help="Work silently."
    )
    parser.add_argument(
        "--epochs", type=int, default=1, help="Minimum number of last epochs to fetch"
    )
