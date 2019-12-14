#!/usr/bin/env python3

import argparse
import os
import subprocess

import _hkml

def set_argparser(parser):
    _hkml.set_manifest_mlist_options(parser, mlist_nargs='+')

def fetch_mail(manifest_file, mail_lists):
    manifest = _hkml.get_manifest(manifest_file)
    if not manifest:
        print("Cannot open manifest file %s" % manifest_file)
        parser.print_help()
        exit(1)

    site = manifest['site']
    for mlist in mail_lists:
        repo_paths = _hkml.mail_list_repo_paths(mlist, manifest)
        local_paths = _hkml.mail_list_data_paths(mlist, manifest)
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
    mail_lists = args.mlist
    fetch_mail(manifest_file, mail_lists)

if __name__ == '__main__':
    main()
