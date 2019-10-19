#!/usr/bin/env python3

import argparse
import os
import subprocess

from _hckmail import *

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', '-m', type=str,
            default=DEFAULT_MANIFEST,
            help='Manifesto file in grok\'s format plus site field.')
    parser.add_argument('lists', type=str, nargs='+',
            help='Name of the mailing list.')

    args = parser.parse_args()
    manifest_file = args.manifest
    mail_lists = args.lists

    manifest = get_manifest(manifest_file)
    if not manifest:
        print("Cannot open manifest file %s" % manifest_file)
        parser.print_help()
        exit(1)

    site = manifest['site']
    for mlist in mail_lists:
        repo_path = mail_list_repo_path(mlist, manifest)
        if not repo_path:
            continue
        print('%s%s' % (site, repo_path))
        git_url = '%s%s' % (site, repo_path)
        local_path = mail_list_data_path(mlist, manifest)
        if not os.path.isdir(local_path):
            cmd = 'git clone --mirror %s %s' % (git_url, local_path)
        else:
            cmd = 'git --git-dir=%s remote update' % local_path
        subprocess.call(cmd.split())

if __name__ == '__main__':
    main()
