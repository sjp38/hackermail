# SPDX-License-Identifier: GPL-2.0

import json
import os

import _hkml

class Note:
    line_nr = None
    note = None

    def __init__(self, line_nr, note):
        self.line_nr = line_nr
        self.note = note

    def to_kvpairs(self):
        return {
                'line_nr': self.line_nr,
                'note': self.note,
                }

    @classmethod
    def from_kvpairs(cls, kvpairs):
        return cls(line_nr=kvpairs['line_nr'], note=kvpairs['note'])

class MailNotes:
    msgid = None
    notes = None

    def __init__(self, msgid, notes):
        self.msgid = msgid
        self.notes = notes

    def to_kvpairs(self):
        return {
                'msgid': self.msgid,
                'notes': [n.to_kvpairs() for n in self.notes],
                }

    @classmethod
    def from_kvpairs(cls, kvpairs):
        return cls(msgid=kvpairs['msgid'],
                   notes=[Note.from_kvpairs(kvp) for kvp in kvpairs['notes']])

def mail_notes_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'mail_notes')

def write_mail_notes_file(notes):
    kvpairs = {
            'mail_notes': [n.to_kvpairs() for n in notes],
            }
    with open(mail_notes_file_path(), 'w') as f:
        json.dump(kvpairs, f, indent=4, sort_keys=True)

def read_mail_notes_file():
    file_path = mail_notes_file_path()
    if not os.path.isfile(file_path):
        return []
    with open(file_path, 'r') as f:
        kvpairs = json.load(f)
    return [MailNotes.from_kvpairs(kvp) for kvp in kvpairs['mail_notes']]
