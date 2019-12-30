#!/usr/bin/env python3

import argparse
import os
import subprocess

import _hkml

def set_argparser(parser):
    _hkml.set_manifest_mlist_options(parser, mlist_nargs='*')
    parser.add_argument('--quiet', '-q', default=False, action='store_true',
            help='Work silently.')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    manifest_file = args.manifest
    if not manifest_file:
        manifest_file = os.path.join(_hkml.get_hkml_dir(), 'manifest')
    mail_lists = args.mlist
    if not mail_lists:
        mail_lists = _hkml.fetched_mail_lists()
    quiet = args.quiet
    _hkml.fetch_mail(manifest_file, mail_lists, quiet)

if __name__ == '__main__':
    main()
