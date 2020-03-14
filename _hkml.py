#!/usr/bin/env python3

import datetime
import json
import os
import subprocess
import sys

class Mail:
    gitid = None
    gitdir = None
    date = None
    subject = None
    orig_subject = None
    tags = None
    series = None
    __mbox_parsed = None
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

    def get_raw_content(self):
        cmd = ["git", "--git-dir=%s" % self.gitdir,
                'show', '%s:m' % self.gitid]
        self.mbox = subprocess.run(cmd,
                stdout=subprocess.PIPE).stdout.decode( 'utf-8').strip()

    def set_mbox_parsed(self):
        if not self.mbox:
            self.get_raw_content()
        self.__mbox_parsed = parse_mbox(self.mbox)

    def get_mbox_parsed(self, tag):
        if not self.__mbox_parsed:
            self.set_mbox_parsed()
        return get_mbox_field(self.__mbox_parsed, tag)

    def get_mbox_parsed_field(self):
        if not self.__mbox_parsed:
            self.set_mbox_parsed()
        return self.__mbox_parsed

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
    mail_dirs = subprocess.check_output(['ls', archive_dir]).decode(
            'utf-8').strip().split('\n')
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

def valid_to_show(mail, tags_to_hide, tags_to_show):
    has_tag = False
    if tags_to_hide:
        for tag in tags_to_hide:
            if tag.lower() in mail.tags:
                has_tag = True
                break
        if has_tag:
            return False

    if tags_to_show:
        for tag in tags_to_show:
            if tag.lower() in mail.tags:
                has_tag = True
                break
        if not has_tag:
            return False
    return True

def filter_mails(args):
    manifest_file = args.manifest
    if not manifest_file:
        manifest_file = os.path.join(get_hkml_dir(), 'manifest')
    mail_list = args.mlist
    since = args.since

    tags_to_show = []
    tags_to_hide = []
    if args.show:
        tags_to_show = args.show.split(',')
    if args.hide:
        tags_to_hide = args.hide.split(',')
    msgid = args.msgid

    idx_of_mail = args.index

    manifest = get_manifest(manifest_file)
    if not manifest:
        print("Cannot open manifest file %s" % manifest_file)
        exit(1)

    lines = []
    mdirs = mail_list_data_paths(mail_list, manifest)
    if not mdirs:
        print("Mailing list '%s' in manifest '%s' not found." % (
            mail_list, manifest_file))
        exit(1)
    for mdir in mdirs:
        cmd = ["git", "--git-dir=%s" % mdir, "log",
                '--date=iso-strict', '--pretty=%h %ad %s (%an)',
                "--since=%s" % since]

        if args.author:
            cmd += ['--author=%s'% args.author]

        mails_to_show = []
        threads = {} # orig_subject -> mails (latest comes first)
        lines += subprocess.check_output(cmd).decode('utf-8').strip().split('\n')

    for line in lines:
        fields = line.split()
        if len(fields) < 3:
            continue
        mail = Mail(fields[0], mdir, fields[1], fields[2:])

        if msgid and mail.get_mbox_parsed('message-id') != ( '<%s>' % msgid):
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

def set_manifest_mlist_options(parser, mlist_nargs='?'):
    parser.add_argument('--manifest', metavar='manifest', type=str,
            help='Manifesto file in grok\'s format plus site field.')
    if not mlist_nargs:
        parser.add_argument('mlist', metavar='mailing list', type=str,
                help='Mailing list to show.')
    else:
        parser.add_argument('mlist', metavar='mailing list', type=str,
                nargs=mlist_nargs, help='Mailing list to show.')

def set_mail_search_options(parser, mlist_nargs='?'):
    DEFAULT_SINCE = datetime.datetime.now() - datetime.timedelta(days=3)
    DEFAULT_SINCE = "%s-%s-%s" % (DEFAULT_SINCE.year, DEFAULT_SINCE.month,
                DEFAULT_SINCE.day)

    set_manifest_mlist_options(parser, mlist_nargs)
    parser.add_argument('--since', metavar='since', type=str,
            default=DEFAULT_SINCE,
            help='Show mails more recent than a specific date.')
    parser.add_argument('--show', metavar='tags', type=str,
            help='Tags seperated by comma.  Show mails having the tags.')
    parser.add_argument('--hide', metavar='tag', type=str,
            help='Tags seperated by comma.  Hide mails having the tags.')
    parser.add_argument('--msgid', metavar='msgid', type=str,
            help='Message Id of the mail to show.')
    parser.add_argument('--author', metavar='msgid', type=str,
            help='Author of the mails.')
    parser.add_argument('--index', '-i', metavar='idx', type=int,
            help='Index of the mail to format reply for.')

def get_mbox_field(parsed, tag):
    tag = tag.lower()
    if tag == 'body':
        return parsed['body']
    heads = parsed['header']
    if tag in heads:
        return heads[tag]
    return None

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
    parsed['body'] = '\n'.join(mbox_lines[idx:])
    return parsed
