#!/usr/bin/env python3

import argparse

import _hkml

def set_argparser(parser):
    _hkml.set_manifest_option(parser)

def pr_list(list_, depth=0):
    indent = ' ' * 4 * depth

    for entry in list:
        if not type(entry) in [dict, list]:
            print('%s%s' % (indent, entry))
        elif type(entry) == dict:
            print('%s{' % indent)
            pr_directory(entry, depth + 1)
            print('%s}' % indent)
        elif type(entry) == list:
            print('%s[' % indent)
            pr_list(entry, depth + 1)
            print('%s]' % indent)

def pr_directory(directory, depth=0):
    indent = ' ' * 4 * depth
    for key in directory:
        val = directory[key]

        if not type(val) in [dict, list]:
            print('%s%s: %s' % (indent, key, val))

        if type(val) == dict:
            print('%s%s: {' % (indent, key))
            pr_directory(val, depth + 1)
            print('%s}' % indent)

        if type(val) == list:
            print('%s%s: [' % (indent, key))
            pr_list(val, depth + 1)
            print('%s]' % indent)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    pr_directory(_hkml.get_manifest(args.manifest))

if __name__ == '__main__':
    main()
