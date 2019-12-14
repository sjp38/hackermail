#!/usr/bin/env python3

import argparse
import os
import subprocess

from _hkml import *

def set_argparser(parser):
    parser.add_argument('--manifest', '-m', type=str,
            default=DEFAULT_MANIFEST,
            help='Manifesto file in grok\'s format plus site field.')
    parser.add_argument('lists', type=str, nargs='+',
            help='Name of the mailing list.')

def fetch_mail(manifest_file, mail_lists):
    manifest = get_manifest(manifest_file)
    if not manifest:
        print("Cannot open manifest file %s" % manifest_file)
        parser.print_help()
        exit(1)

    site = manifest['site']
    for mlist in mail_lists:
        repo_paths = mail_list_repo_paths(mlist, manifest)
        local_paths = mail_list_data_paths(mlist, manifest)
        for idx, repo_path in enumerate(repo_paths):
            git_url = '%s%s' % (site, repo_path)
            local_path = local_paths[idx]
            if not os.path.isdir(local_path):
                cmd = 'git clone --mirror %s %s' % (git_url, local_path)
            else:
                cmd = 'git --git-dir=%s remote update' % local_path
            print(cmd)
            subprocess.call(cmd.split())

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    manifest_file = args.manifest
    mail_lists = args.lists
    fetch_mail(manifest_file, mail_lists)

if __name__ == '__main__':
    main()
