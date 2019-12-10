#!/usr/bin/env python3

import json
import subprocess

class Mail:
    gitid = None
    gitdir = None
    date = None
    subject = None
    orig_subject = None
    tags = None
    series = None
    mbox_parsed = None
    mbox = None

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

        self.set_mbox_parsed()

    def get_raw_content(self):
        cmd = ["git", "--git-dir=%s" % self.gitdir,
                'show', '%s:m' % self.gitid]
        self.mbox = subprocess.run(cmd,
                stdout=subprocess.PIPE).stdout.decode( 'utf-8').strip()

    def set_mbox_parsed(self):
        if not self.mbox:
            self.get_raw_content()
        self.mbox_parsed = parse_mbox(self.mbox)

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

def valid_to_show(mail, tags_to_hide, tags_to_show):
    has_tag = False
    if tags_to_hide:
        for tag in tags_to_hide:
            if tag in mail.tags:
                has_tag = True
                break
        if has_tag:
            return False

    if tags_to_show:
        for tag in tags_to_show:
            if tag in mail.tags:
                has_tag = True
                break
        if not has_tag:
            return False
    return True

def filter_mails(manifest, mail_list, since, tags_to_show, tags_to_hide, msgid,
        idx_of_mail):
    mdir = mail_list_data_path(mail_list, manifest)

    cmd = ["git", "--git-dir=%s" % mdir, "log",
            '--date=iso-strict', '--pretty=%h %ad %s (%an)',
            "--since=%s" % since]

    mails_to_show = []
    threads = {} # orig_subject -> mails (latest comes first)
    lines = subprocess.check_output(cmd).decode('utf-8').strip().split('\n')
    for line in lines:
        fields = line.split()
        if len(fields) < 3:
            continue
        mail = Mail(fields[0], mdir, fields[1], fields[2:])

        if msgid and mail.mbox_parsed['header']['message-id'] != (
                '<%s>' % msgid):
            continue

        if not valid_to_show(mail, tags_to_hide, tags_to_show):
            continue

        # Shows only latest reply for given mail
        if mail.orig_subject in threads:
            threads[mail.orig_subject].append(mail)
            if not 'reply' in mail.tags:
                latest_reply = threads[mail.orig_subject][0]
                if latest_reply in mails_to_show:
                    mails_to_show.remove(latest_reply)
                    mails_to_show.append(mail)
            continue
        threads[mail.orig_subject] = [mail]

        mails_to_show.append(mail)

    mails_to_show.reverse()
    if idx_of_mail:
        mails_to_show = [mails_to_show[idx_of_mail]]
    return mails_to_show, threads

def parse_mbox(mbox):
    in_header = True
    head_fields = {}
    mbox_lines = mbox.split('\n')
    for idx, line in enumerate(mbox_lines):
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
    parsed = {}
    parsed['header'] = head_fields
    parsed['body'] = '\n'.join(mbox_lines[idx + 1:])
    return parsed
