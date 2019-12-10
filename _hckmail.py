#!/usr/bin/env python3

import json
import subprocess

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

class Mail:
    gitid = None
    gitdir = None
    date = None
    subject = None
    orig_subject = None
    tags = None
    series = None
    mail_content = None

    def __init__(self, gitid, gitdir, date, subject_fields):
        self.gitid = gitid
        self.gitdir = gitdir
        self.date = date
        self.subject = ' '.join(subject_fields)
        self.orig_subject = self.subject
        self.tags = []

        re_depth = 0
        for f in subject_fields:
            if f.lower() == 're:':
                re_depth += 1
            else:
                break
        if re_depth > 0:
            self.tags.append('reply')
            self.orig_subject = ' '.join(subject_fields[re_depth:])

        if self.orig_subject[0] == '[':
            tag = self.orig_subject[1:].split(']')[0].strip().lower()
            self.tags += tag.split()

            series = self.tags[-1].split('/')
            if (len(series) == 2 and series[0].isdigit() and
                    series[1].isdigit()):
                self.series = [int(x) for x in series]

        self.set_mail_content()

    def set_mail_content(self):
        cmd = ["git", "--git-dir=%s" % self.gitdir,
                'show', '%s:m' % self.gitid]
        mail_content_raw = subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode(
                'utf-8').strip()
        in_header = True
        head_fields = {}
        for idx, line in enumerate(mail_content_raw.split('\n')):
            if in_header:
                if line and line[0] in [' ', '\t'] and key:
                    head_fields[key] += ' %s' % line.strip()
                    continue
                line = line.strip()
                key = line.split(':')[0].lower()
                if key:
                    head_fields[key] = line[len(key) + 2:]
                elif line == '':
                    in_header = False
                continue
            break
        self.mail_content = {}
        self.mail_content['header'] = head_fields
        self.mail_content['body'] = mail_content_raw[idx + 1:]
