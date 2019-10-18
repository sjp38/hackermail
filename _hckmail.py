#!/usr/bin/env python3

import json

HCKMAILDIR = '.hkm'
DEFAULT_MANIFEST = HCKMAILDIR + '/manifest'
MAILDAT_DIR = HCKMAILDIR + '/archives'

def get_manifest(manifest_file):
    try:
        with open(manifest_file) as f:
            manifest = json.load(f)
    except FileNotFoundError:
        return None
    return manifest

def mail_list_repo_path(mail_list, manifest):
    for path in manifest:
        if path.startswith('/%s/' % mail_list):
            return path

def mail_list_data_path(mail_list, manifest):
    repo_path = mail_list_repo_path(mail_list, manifest)
    if repo_path:
        return MAILDAT_DIR + repo_path
