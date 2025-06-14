#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import json
import os
import shutil
import subprocess
import tempfile

import _hkml


def need_to_print(key, depth, mlists):
    if depth > 0:
        return True
    if not mlists:
        return True

    # expected key: /linux-bluetooth/git/0.git
    if key[-4:].strip() != ".git":
        return False
    fields = key.split("/")
    if len(fields) != 4:
        print(fields)
        return False
    return fields[1] in mlists


def pr_directory(directory, mlists, depth=0):
    indent = " " * 4 * depth
    for key in directory:
        if not need_to_print(key, depth, mlists):
            continue

        val = directory[key]

        if type(val) == dict:
            print("%s%s: {" % (indent, key))
            pr_directory(val, mlists, depth + 1)
            print("%s}" % indent)
        else:
            print("%s%s: %s" % (indent, key, val))


def fetch_lore(output_file=None):
    """
    Fetch lore manifest and use it.
    Returns an error string or None if no error happened.
    """
    # Get the current working directory
    original_dir = os.getcwd()
    temp_dir = tempfile.mkdtemp(prefix="hkml_manifest_dir_")
    os.chdir(temp_dir)

    err = subprocess.call(["wget", "https://lore.kernel.org/manifest.js.gz"])
    if err:
        return "downloading lore manifest fail (%s); please cleanup %s" % (
            err,
            temp_dir,
        )
    err = subprocess.call(["gzip", "-d", "manifest.js.gz"])
    if err:
        return "gunzip fail (%s); please cleanup %s" % (err, temp_dir)
    with open("manifest.js") as f:
        manifest = json.load(f)
    os.chdir(original_dir)
    shutil.rmtree(temp_dir)
    manifest["site"] = "https://lore.kernel.org"
    if output_file is None:
        _hkml.update_manifest(manifest)
    else:
        with open(output_file, "w") as f:
            json.dump(manifest, f, indent=4)
    return None


def main(args):
    if args.action == "fetch_lore":
        err = fetch_lore(args.fetch_lore_output)
        if err:
            print(err)
            exit(1)
        return

    manifest = args.manifest
    _hkml.set_hkml_dir_manifest(args.hkml_dir, manifest)
    if args.action == "list":
        if args.mailing_lists is True:
            for key in _hkml.get_manifest():
                fields = key.split("/")
                if len(fields) > 1:
                    print(fields[1])
            return
        pr_directory(_hkml.get_manifest(), args.mlists)
    elif args.action == "convert_public_inbox_manifest":
        if not args.public_inbox_manifest or not args.site:
            print("--public_inbox_manifest or --site is not set")
            exit(1)
        with open(args.public_inbox_manifest) as f:
            manifest = json.load(f)
        manifest["site"] = args.site
        print(json.dumps(manifest))
    elif args.action == "fetch_lore":
        err = fetch_lore(args.fetch_lore_output)
        if err is not None:
            print(err)
            exit(1)


def set_argparser(parser):
    _hkml.set_manifest_option(parser)
    parser.add_argument(
        "action",
        metavar="<action>",
        nargs="?",
        choices=["list", "convert_public_inbox_manifest", "fetch_lore"],
        default="list",
        help="action to do: list, fetch_lore or convert_public_inbox_manifest",
    )
    parser.add_argument(
        "--mlists",
        metavar="<mailing list name>",
        nargs="+",
        help="print manifest entries for specific mailing lists",
    )
    parser.add_argument(
        "--public_inbox_manifest",
        metavar="<file>",
        help="public inbox manifest which want to convert for hackermail",
    )
    parser.add_argument("--site", metavar="<url>", help="site to fetch mail archives")
    parser.add_argument(
        "--mailing_lists", action="store_true", help="list only names of mailine lists"
    )
    parser.add_argument(
        "--fetch_lore_output",
        metavar="<file>",
        help="store fetched lore manifest to given file",
    )
