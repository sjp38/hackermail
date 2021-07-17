#!/usr/bin/env python3

import argparse

import _hkml

def set_argparser(parser):
    _hkml.set_manifest_option(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    manifest = _hkml.get_manifest(args.manifest)
    print(manifest)

if __name__ == '__main__':
    main()
