#!/usr/bin/env python3

import base64
import datetime
import json
import mailbox
import os
import subprocess
import sys

def cmd_str_output(cmd):
    output = subprocess.check_output(cmd)
    try:
        return output.decode('utf-8').strip()
    except UnicodeDecodeError as e:
        return output.decode('cp437').strip()

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
    def from_gitlog(cls, gitid, gitdir, date, subject):
        self = cls()
        self.gitid = gitid
        self.gitdir = gitdir
        self.git_date = date
        self.git_subject = subject
        self.orig_subject = self.git_subject
        self.tags = []

        re_depth = 0
        subject_fields = subject.split()
        for f in subject_fields:
            if f.lower() == 're:':
                re_depth += 1
            else:
                break
        if re_depth > 0:
            self.tags.append('reply')
            self.orig_subject = ' '.join(subject_fields[re_depth:])

        if len(self.orig_subject) > 0 and self.orig_subject[0] == '[':
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
            cmd = ['git', '--git-dir=%s' % self.gitdir,
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
                    val = line[len(key) + 2:]
                    if key == 'message-id':
                        if len(val.split()) >= 1:
                            val = val.split()[0]
                    parsed[key] = val
                elif line == '':
                    in_header = False
                continue
            break
        try:
            # 'm' doesn't have start 'From' line in some case.  Add a fake one.
            mbox_str = '\n'.join(['From mboxrd@z Thu Jan  1 00:00:00 1970',
                self.mbox])
            parsed['body'] = mailbox.Message(
                    mbox_str).get_payload(decode=True).decode()
        except:
            # Still decode() could fail due to encoding
            parsed['body'] = '\n'.join(mbox_lines[idx:])

            encoding_key = 'Content-Transfer-Encoding'.lower()
            if encoding_key in parsed and parsed[encoding_key] == 'base64':
                try:
                    parsed['body'] = base64.b64decode(parsed['body']).decode()
                except:
                    pass

        if 'date' in parsed:
            tokens = parsed['date'].split()
            if tokens[-2:] == ['[thread', 'overview]']:
                parsed['date'] = ' '.join(tokens[:-2])

        self.__mbox_parsed = parsed

def read_mbox_file(filepath):
    mails = []
    for message in mailbox.mbox(filepath):
        mails.append(Mail.from_mbox('%s' % message))
    return mails

__hkml_dir = None

def set_hkml_dir(path=None):
    global __hkml_dir
    if path:
        if not os.path.exists(path):
            sys.stderr.write('Given hkml_dir %s does not exists\n' % path)
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
        sys.stderr.write('hkml metadata directory is not found from\n')
        sys.stderr.write('    \'$HKML_DIR\' (%s),\n' % env_dir)
        sys.stderr.write('    current directory (%s),\n' % cwd_dir)
        sys.stderr.write('    \'hkml\' binary directory (%s), and\n' % cwd_dir)
        sys.stderr.write('    your home directory (%s)\n' % cwd_dir)
        sys.stderr.write('have you forgot running \'hkml init\'?\n')
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

def __get_epoch_from_git_path(git_path):
    # git_path is, e.g., '.../0.git'
    return int(os.path.basename(git_path).split('.git')[0])

def mail_list_repo_paths(mail_list, manifest):
    '''Returns git trees in the manifest for the given mailing lists.

    Note that the paths are sorted by the epochs of the git trees in
    descsending order.'''
    paths = []
    for path in manifest:
        if path.startswith('/%s/' % mail_list):
            paths.append(path)
    return sorted(paths, key=__get_epoch_from_git_path, reverse=True)

def mail_list_data_paths(mail_list, manifest):
    '''Returns git trees in this machine for the given mailing lists.

    Note that the paths are sorted by the epochs of the git trees in
    descsending order.'''

    repo_paths = mail_list_repo_paths(mail_list, manifest)
    mdir_paths = []
    for path in repo_paths:
        mdir_paths.append(os.path.join(get_hkml_dir(), 'archives' + path))
    return sorted(mdir_paths, key=__get_epoch_from_git_path, reverse=True)

def set_manifest_option(parser):
    parser.add_argument('--manifest', metavar='<file>', type=str,
            help='Manifesto file in grok\'s format plus site field.')
