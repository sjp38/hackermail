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

global_mail_notes = None

def get_mail_notes():
    global global_mail_notes
    if global_mail_notes is None:
        global_mail_notes = read_mail_notes_file()
    return global_mail_notes

def main(args):
    print('under construction')
    exit(1)

def set_argparser(parser):
    parser.description = 'manage notes on mail'

    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>')

    parser_list = subparsers.add_parser('list', help='list notest')
    parser_list.add_argument('--msgid', metavar='<message id>', nargs='+',
                             help='message id of mails to show notes for')

    parser_add = subparsers.add_parser('add', help='add a note')
    parser_add.add_argument('msgid', metavar='<message id>',
                            help='message id of mail to add notes for')
    parser_add.add_argument('line_nr', metavar='<line number>',
                            help='line number of the mail to add note for')
    parser_add.add_argument('note', metavar='<text>',
                            help='the note to add')

    parser_remove = subparsers.add_parser('remove', help='remove a note')
    parser_remove.add_argument('msgid', metavar='<message id>',
                               help='message id of mail to add notes for')
    parser_remove.add_argument('line_nr', metavar='<line number>',
                               help='line number of the mail to add note for')
    parser_remove.add_argument('note_idx', metavar='<note idx>', nargs='+',
                               help='indices of notes to remove')
