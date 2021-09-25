#!/usr/bin/env python3

import argparse
import os
import subprocess

import _hkml

def get_epoch_from_git_path(git_path):
    # git_path is, e.g., '.../0.git'
    return int(git_path.split('/')[-1].split('.git')[0])

def fetch_mail(manifest_file, mail_lists, quiet=False, epochs=1):
    manifest = _hkml.get_manifest(manifest_file)
    if not manifest:
        print('Cannot open manifest file (%s)' % manifest_file)
        exit(1)

    site = manifest['site']
    for mlist in mail_lists:
        repo_paths = sorted(_hkml.mail_list_repo_paths(mlist, manifest),
                key=get_epoch_from_git_path)[-1 * epochs:]
        local_paths = sorted(_hkml.mail_list_data_paths(mlist, manifest),
                key=get_epoch_from_git_path)[-1 * epochs:]

        for idx, repo_path in enumerate(repo_paths):
            git_url = '%s%s' % (site, repo_path)
            local_path = local_paths[idx]
            if not os.path.isdir(local_path):
                cmd = 'git clone --mirror %s %s' % (git_url, local_path)
            else:
                cmd = 'git --git-dir=%s remote update' % local_path
            if not quiet:
                print(cmd)
                subprocess.call(cmd.split())
            else:
                with open(os.devnull, 'w') as f:
                    subprocess.call(cmd.split(), stdout=f)

def fetched_mail_lists():
    archive_dir = os.path.join(_hkml.get_hkml_dir(), 'archives')
    mail_dirs = _hkml.cmd_lines_output(['ls', archive_dir])
    return [x for x in mail_dirs if x != '' and os.path.isdir(
        os.path.join(archive_dir, x))]

def set_argparser(parser):
    _hkml.set_manifest_mlist_options(parser, mlist_nargs='*')
    parser.add_argument('--quiet', '-q', default=False, action='store_true',
            help='Work silently.')
    parser.add_argument('--epochs', type=int, default=1,
            help='Number of last epochs to fetch (0 for all)')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    mail_lists = args.mlist
    manifest_file = args.manifest
    if not mail_lists:
        mail_lists = fetched_mail_lists()
    if not mail_lists:
        print('mail lists to fetch is not specified')
        exit(1)
    quiet = args.quiet
    fetch_mail(manifest_file, mail_lists, quiet, args.epochs)

if __name__ == '__main__':
    main()
