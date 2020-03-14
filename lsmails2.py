#!/usr/bin/env python3

import _hkml

class Mail:
    fields = None
    mbox = None

    def __init__(self, mbox):
        self.mbox = mbox
        parsed = _hkml.parse_mbox(mbox)
        self.fields = parsed['header']
        self.fields['body'] = parsed['body']

    def get_field(self, key):
        return self.fields[key]

    def set_field(self, key, val):
        self.fields[key] = val

class HackerMail:
    gitdir = None
    gitid = None
    mail = None

    def __init__(self, gitdir, gitid):
        self.gitdir = gitdir
        self.gitid = gitid
        cmd = ['git', '--git-dir=$s' % gitdir, 'show', '%s:m' % gitid]
        mbox = subprocess.run(cmd,
                stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
        self.mail = Mail(mbox)

    def get_field(self, key):
        return self.mail.get_field(key)

    def set_field(self, key, val):
        return self.mail.set_field(key, val)

print('hello')
