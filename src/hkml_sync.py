# SPDX-License-Identifier: GPL-2.0

import os
import subprocess

import _hkml

"""
Synchronize personal files in .hkm/ via user-specified git repo.
"""


def files_to_sync(hkml_dir):
    files = ["manifest", "monitor_requests", "tags"]
    for filename in os.listdir(hkml_dir):
        if filename.startswith("tags_"):
            files.append(filename)
    return files


def commit_changes(hkml_dir):
    git_cmd = ["git", "-C", hkml_dir]
    for file in files_to_sync(hkml_dir):
        file_path = os.path.join(hkml_dir, file)
        if os.path.isfile(file_path):
            if subprocess.call(git_cmd + ["add", file]) != 0:
                print("git-addding file (%s) failed" % file_path)
                exit(1)
        else:
            # may fail if already removed, or this is first call
            subprocess.call(git_cmd + ["rm", file_path])
    # don't check the return value, since it could fail if no change is really
    # made.
    subprocess.call(git_cmd + ["commit", "-m", "hkml sync commit"])


def setup_git(hkml_dir, remote):
    if remote is None:
        print("This is initial time of sync.  Please provide --remote")
        exit(1)
    git_cmd = ["git", "-C", hkml_dir]
    if subprocess.call(git_cmd + ["init"]) != 0:
        print("git initializing failed")
        eixt(1)
    if subprocess.call(git_cmd + ["remote", "add", "sync-target", remote]) != 0:
        print("adding remote failed")
        exit(1)
    if subprocess.call(git_cmd + ["fetch", "sync-target"]) != 0:
        print("fetching remote failed")
        exit(1)
    branches = subprocess.check_output(git_cmd + ["branch", "-r"]).decode().split()
    if "sync-target/latest" in branches:
        if subprocess.call(git_cmd + ["reset", "--hard", "sync-target/latest"]) != 0:
            print("checking remote out failed")
            exit(1)


def syncup(hkml_dir, remote):
    git_cmd = ["git", "-C", hkml_dir]

    commit_changes(hkml_dir)

    if remote is not None:
        cmd = git_cmd + ["remote", "get-url", "sync-target"]
        current_sync_target = subprocess.check_output(cmd).decode().strip()
        if remote != current_sync_target:
            cmd = git_cmd + ["remote", "set-url", "sync-target", remote]
            if subprocess.call(cmd) != 0:
                print("remote url update failed")

    if subprocess.call(git_cmd + ["fetch", "sync-target"]) != 0:
        print("fetching remote failed")
        exit(1)
    if subprocess.call(git_cmd + ["rebase", "sync-target/latest"]) != 0:
        print("rebasing failed")
        exit(1)

    if subprocess.call(git_cmd + ["push", "sync-target", "HEAD:latest"]) != 0:
        print("push failed")
        exit(1)


def syncup_ready():
    return os.path.isdir(os.path.join(_hkml.get_hkml_dir(), ".git"))


def main(args):
    if not syncup_ready():
        setup_git(_hkml.get_hkml_dir(), args.remote)
    syncup(_hkml.get_hkml_dir(), args.remote)


def set_argparser(parser):
    parser.description = "synchronize the outputs and setups"
    parser.add_argument(
        "--remote", metavar="<git repo>", help="remote git repo to synchronize with"
    )
