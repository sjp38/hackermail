# SPDX-License-Identifier: GPL-2.0

import os
import subprocess

import _hkml

'''
Synchronize personal files in .hkm/ via user-specified git repo.
'''

def setup_git(hkml_dir, remote):
    if remote is None:
        print('This is initial time of sync.  Please provide --remote')
        exit(1)
    git_cmd = ['git', '-C', hkml_dir]
    if subprocess.call(git_cmd + ['init']) != 0:
        print('git initializing failed')
        eixt(1)
    if subprocess.call(
            git_cmd + ['remote', 'add', 'sync-target', remote]) != 0:
        print('adding remote failed')
        exit(1)
    if subprocess.call(git_cmd + ['fetch', 'sync-target']) != 0:
        print('fetching remote failed')
        exit(1)
    branches = subprocess.check_output(
            git_cmd + ['branch', '-a']).decode().split()
    if 'sync-target/latest' in branches:
        if subprocess.git(
                git_cmd + ['reset', '--hard', 'sync-target/latest']) != 0:
            print('checking remote out failed')
            exit(1)

    for file in ['manifest', 'monitor_requests', 'tags']:
        file_path = os.path.join(hkml_dir, file)
        if os.path.isfile(file_path):
            if subprocess.call(git_cmd + ['add', file_path]) != 0:
                print('git-addding file (%s) failed' % file_path)
                exit(1)
    if subprocess.call(git_cmd + ['commit', '-m', 'hkml sync commit']) != 0:
        print('git-commit failed')
        exit(1)

    if subprocess.call(git_cmd + ['push', 'sync-target', 'HEAD:latest']) != 0:
        print('push failed')
        exit(1)

def syncup(hkml_dir):
    git_cmd = ['git', '-C', hkml_dir]

    for file in ['manifest', 'monitor_requests', 'tags']:
        file_path = os.path.join(hkml_dir, file)
        if os.path.isfile(file_path):
            if subprocess.call(git_cmd + ['add', file_path]) != 0:
                print('git-addding file (%s) failed' % file_path)
                exit(1)

    # if there's no change, this will fail.  But don't care because later
    # rebase/push will fail if something wrong in real.
    subprocess.call(git_cmd + ['commit', '-m', 'hkml sync commit'])

    if subprocess.call(git_cmd + ['fetch', 'sync-target']) != 0:
        print('fetching remote failed')
        exit(1)
    if subprocess.call(git_cmd + ['rebase', 'sync-target/latest']) != 0:
        print('rebasing failed')
        exit(1)

    if subprocess.call(git_cmd + ['push', 'sync-target', 'HEAD:latest']) != 0:
        print('push failed')
        exit(1)

def main(args):
    hkml_dir = _hkml.get_hkml_dir()
    if not os.path.isdir(os.path.join(hkml_dir, '.git')):
        setup_git(hkml_dir, args.remote)
    syncup(hkml_dir)

def set_argparser(parser):
    parser.description = 'synchronize the outputs and setups'
    parser.add_argument('--remote', metavar='<git repo>',
                        help='remote git repo to synchronize with')
