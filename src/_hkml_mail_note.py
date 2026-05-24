# SPDX-License-Identifier: GPL-2.0

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
