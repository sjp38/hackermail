#!/usr/bin/env python3

import datetime
import json
import os
import subprocess
import sys

def cmd_str_output(cmd):
    try:
        return subprocess.check_output(cmd).decode('cp437').strip()
    except UnicodeDecodeError as e:
        print('could not decode cmd (%s) output: %s' % (cmd, e))
        return ''

def cmd_lines_output(cmd):
    return cmd_str_output(cmd).split('\n')

class Mail:
    gitid = None
    gitdir = None
    git_date = None
    git_subject = None
    orig_subject = None
    tags = None
    series = None
    __mbox_parsed = None
    mbox = None
    replies = None

    def __init__(self):
        self.replies = []

    @classmethod
    def from_gitlog(cls, gitid, gitdir, date, subject_fields):
        self = cls()
        self.gitid = gitid
        self.gitdir = gitdir
        self.git_date = date
        self.git_subject = ' '.join(subject_fields)
        self.orig_subject = self.git_subject
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
        return self

    @classmethod
    def from_mbox(cls, mbox):
        self = cls()
        self.mbox = mbox
        self.__parse_mbox()
        return self

    def get_field(self, tag):
        tag = tag.lower()
        # this might set from git log
        if tag == 'subject' and self.git_subject:
            return self.git_subject
        if tag == 'date' and self.git_date:
            return self.git_date

        if not self.__mbox_parsed:
            self.__parse_mbox()

        if not tag in self.__mbox_parsed:
            return None
        return self.__mbox_parsed[tag]

    def __parse_mbox(self):
        if not self.mbox:
            if not self.gitdir or not self.gitid:
                print('cannot get mbox')
                exit(1)
            cmd = ["git", "--git-dir=%s" % self.gitdir,
                    'show', '%s:m' % self.gitid]
            self.mbox = cmd_str_output(cmd)

        in_header = True
        parsed = {}
        mbox_lines = self.mbox.split('\n')
        for idx, line in enumerate(mbox_lines):
            if in_header:
                if line and line[0] in [' ', '\t'] and key:
                    parsed[key] += ' %s' % line.strip()
                    continue
                line = line.strip()
                key = line.split(':')[0].lower()
                if key:
                    parsed[key] = line[len(key) + 2:]
                elif line == '':
                    in_header = False
                continue
            break
        parsed['body'] = '\n'.join(mbox_lines[idx:])

        self.__mbox_parsed = parsed

__hkml_dir = None

def set_hkml_dir(path=None):
    global __hkml_dir
    if path:
        if not os.path.exists(path):
            sys.stderr.write("Given hkml_dir %s does not exists\n" % path)
            exit(1)
        __hkml_dir = path
        return

    THE_DIR='.hkm'
    env_dir = os.getenv('HKML_DIR')
    if env_dir and os.path.exists(env_dir):
        __hkml_dir = env_dir
    cwd_dir = os.path.join(os.getcwd(), THE_DIR)
    if cwd_dir and os.path.exists(cwd_dir):
        __hkml_dir = cwd_dir
    bin_dir = os.path.join(os.path.dirname(sys.argv[0]), THE_DIR)
    if bin_dir and os.path.exists(bin_dir):
        __hkml_dir = bin_dir
    home_dir = os.path.join(os.getenv('HOME'), THE_DIR)
    if home_dir and os.path.exists(home_dir):
        __hkml_dir = home_dir
    if not __hkml_dir:
        sys.stderr.write("Couldn't get hkml dir;\n")
        sys.stderr.write("Tried '%s', '%s', '%s' and '%s'\n" %
                (env_dir, cwd_dir, bin_dir, home_dir))
        exit(1)

def get_hkml_dir():
    if not __hkml_dir:
        set_hkml_dir()
    return __hkml_dir

def get_manifest(manifest_file):
    if not manifest_file:
        manifest_file = os.path.join(get_hkml_dir(), 'manifest')

    try:
        with open(manifest_file) as f:
            manifest = json.load(f)
    except:
        return None
    return manifest

def mail_list_repo_paths(mail_list, manifest):
    paths = []
    for path in manifest:
        if path.startswith('/%s/' % mail_list):
            paths.append(path)
    return paths

def fetched_mail_lists():
    archive_dir = os.path.join(get_hkml_dir(), 'archives')
    mail_dirs = cmd_lines_output(['ls', archive_dir])
    return [x for x in mail_dirs if os.path.isdir(
        os.path.join(archive_dir, x))]

def fetch_mail(manifest_file, mail_lists, quiet=False):
    manifest = get_manifest(manifest_file)
    if not manifest:
        print("Cannot open manifest file %s" % manifest_file)
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
            if not quiet:
                print(cmd)
                subprocess.call(cmd.split())
            else:
                with open(os.devnull, 'w') as f:
                    subprocess.call(cmd.split(), stdout=f)

def mail_list_data_paths(mail_list, manifest):
    repo_paths = mail_list_repo_paths(mail_list, manifest)
    mdir_paths = []
    for path in repo_paths:
        mdir_paths.append(os.path.join(get_hkml_dir(), 'archives' + path))
    return mdir_paths

def set_manifest_mlist_options(parser, mlist_nargs='?'):
    parser.add_argument('--manifest', metavar='manifest', type=str,
            help='Manifesto file in grok\'s format plus site field.')
    if not mlist_nargs:
        parser.add_argument('mlist', metavar='mailing list', type=str,
                help='Mailing list to show.')
    else:
        parser.add_argument('mlist', metavar='mailing list', type=str,
                nargs=mlist_nargs, help='Mailing list to show.')
