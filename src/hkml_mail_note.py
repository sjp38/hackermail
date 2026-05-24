# SPDX-License-Identifier: GPL-2.0

import json
import os

import _hkml

class LineNotes:
    line_nr = None
    notes = None    # list of texts

    def __init__(self, line_nr, notes):
        self.line_nr = line_nr
        self.notes = notes

    def to_kvpairs(self):
        return {
                'line_nr': self.line_nr,
                'notes': self.notes,
                }

    @classmethod
    def from_kvpairs(cls, kvpairs):
        return cls(line_nr=kvpairs['line_nr'], notes=kvpairs['notes'])

class MailNotes:
    msgid = None
    line_notes = None   # list of LineNotes objects

    def __init__(self, msgid, line_notes):
        self.msgid = msgid
        self.line_notes = line_notes

    def to_kvpairs(self):
        return {
                'msgid': self.msgid,
                'line_notes': [n.to_kvpairs() for n in self.line_notes],
                }

    @classmethod
    def from_kvpairs(cls, kvpairs):
        return cls(msgid=kvpairs['msgid'],
                   line_notes=[LineNotes.from_kvpairs(kvp)
                               for kvp in kvpairs['line_notes']])

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
    full_mail_notes = get_mail_notes()
    if args.action == 'list':
        if args.msgid is None:
            mail_notes = full_mail_notes
        else:
            mail_notes = [n for n in full_mail_notes if n.msgid in args.msgid]
        for mail_note in mail_notes:
            for line_note in mail_note.line_notes:
                print('%s:%s' % (
                    mail_note.msgid, line_note.line_nr))
                for idx, note in enumerate(line_note.notes):
                    print('- %d: %s' % (idx, note))
    elif args.action == 'add':
        mail_note = None
        for mnote in full_mail_notes:
            if mnote.msgid == args.msgid:
                mail_note = mnote
                break
        if mail_note is None:
            mail_note = MailNotes(args.msgid, [])
            full_mail_notes.append(mail_note)
        line_notes = None
        for lnote in mail_note.line_notes:
            if lnote.line_nr == args.line_nr:
                line_notes = lnote
                break
        if line_notes is None:
            line_notes = LineNotes(args.line_nr, [])
            mail_note.line_notes.append(line_notes)
        line_notes.notes.append(args.note)
        write_mail_notes_file(full_mail_notes)
    elif args.action == 'remove':
        mail_note = None
        for mnote in full_mail_notes:
            if mnote.msgid == args.msgid:
                mail_note = mnote
                break
        if mail_note is None:
            print('no note of the msgid')
            exit(1)
        line_notes = None
        for lnote in mail_note.line_notes:
            if lnote.line_nr == args.line_nr:
                line_notes = lnote
                break
        if line_notes is None:
            print('no note of the line_nr')
            exit(1)
        if args.note_idx >= len(line_notes.notes):
            print('note_idx error')
            exit(1)
        del line_notes.notes[args.note_idx]
        if len(line_notes.notes) == 0:
            mail_note.line_notes.remove(line_notes)
        if len(mail_note.line_notes) == 0:
            full_mail_notes.remove(mail_note)

        write_mail_notes_file(full_mail_notes)

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
    parser_add.add_argument('line_nr', metavar='<line number>', type=int,
                            help='line number of the mail to add note for')
    parser_add.add_argument('note', metavar='<text>',
                            help='the note to add')

    parser_remove = subparsers.add_parser('remove', help='remove a note')
    parser_remove.add_argument('msgid', metavar='<message id>',
                               help='message id of mail to add notes for')
    parser_remove.add_argument('line_nr', metavar='<line number>', type=int,
                               help='line number of the mail to add note for')
    parser_remove.add_argument('note_idx', metavar='<note idx>', type=int,
                               help='indices of notes to remove')
