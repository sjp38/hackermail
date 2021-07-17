#!/usr/bin/env python3

import argparse

import _hkml

def set_argparser(parser):
    _hkml.set_manifest_option(parser)
    parser.add_argument('--mlists', metavar='<mailing list name>', nargs='+',
            help='print manifest entries for specific mailing lists')

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

    pr_directory(_hkml.get_manifest(args.manifest), args.mlists)

if __name__ == '__main__':
    main()
