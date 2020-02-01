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

    def set_fields(self, key, val):
        self.fields[key] = val

print('hello')
