#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import json

import _hkml

def set_argparser(parser):
    _hkml.set_manifest_option(parser)
    parser.add_argument('action', metavar='<action>', nargs='?',
            choices=['list', 'convert_public_inbox_manifest'], default='list',
            help='action to do: list or convert_public_inbox_manifest')
    parser.add_argument('--mlists', metavar='<mailing list name>', nargs='+',
            help='print manifest entries for specific mailing lists')
    parser.add_argument('--public_inbox_manifest', metavar='<file>',
            help='public inbox manifest which want to convert for hackermail')
    parser.add_argument('--site', metavar='<url>',
            help='site to fetch mail archives')

def need_to_print(key, depth, mlists):
    if depth > 0:
        return True
    if not mlists:
        return True

    # expected key: /linux-bluetooth/git/0.git
    if key[-4:].strip() != '.git':
        return False
    fields = key.split('/')
    if len(fields) != 4:
        print(fields)
        return False
    return fields[1] in mlists

def pr_directory(directory, mlists, depth=0):
    indent = ' ' * 4 * depth
    for key in directory:
        if not need_to_print(key, depth, mlists):
            continue

        val = directory[key]

        if type(val) == dict:
            print('%s%s: {' % (indent, key))
            pr_directory(val, mlists, depth + 1)
            print('%s}' % indent)
        else:
            print('%s%s: %s' % (indent, key, val))

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.action == 'list':
        pr_directory(_hkml.get_manifest(), args.mlists)
    elif args.action == 'convert_public_inbox_manifest':
        if not args.public_inbox_manifest or not args.site:
            print('--public_inbox_manifest or --site is not set')
            exit(1)
        with open(args.public_inbox_manifest) as f:
            manifest = json.load(f)
        manifest['site'] = args.site
        print(json.dumps(manifest))

if __name__ == '__main__':
    main()
