# SPDX-License-Identifier: GPL-2.0

import json
import os

import _hkml

class Note:
    text = None # string

    def __init__(self, text):
        self.text = text

    def to_kvpairs(self):
        return {
                'text': self.text,
                }

    @classmethod
    def from_kvpairs(cls, kvpairs):
        return cls(text=kvpairs['text'])

class Notes:
    msgid = None
    line_notes = None   # line number: Note dict

    def __init__(self, msgid, line_notes):
        self.msgid = msgid
        self.line_notes = line_notes

    def to_kvpairs(self):
        line_notes_kvpairs = {}
        for line_nr, notes in self.line_notes.items():
            notes = [note.to_kvpairs() for note in notes]
            line_notes_kvpairs[line_nr] = notes
        return {
                'msgid': self.msgid,
                'line_notes': line_notes_kvpairs,
                }

    @classmethod
    def from_kvpairs(cls, kvpairs):
        line_notes_kvpairs = kvpairs['line_notes']
        line_notes = {}
        for line_nr, notes_kvpairs in line_notes_kvpairs.items():
            notes = [Note.from_kvpairs(kvp) for kvp in notes_kvpairs]
            # json.dump() automatically convert key to string
            line_nr = int(line_nr)
            line_notes[line_nr] = notes
        return cls(msgid=kvpairs['msgid'], line_notes=line_notes)

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
    return [Notes.from_kvpairs(kvp) for kvp in kvpairs['mail_notes']]

global_mail_notes = None

def get_mail_notes():
    global global_mail_notes
    if global_mail_notes is None:
        global_mail_notes = read_mail_notes_file()
    return global_mail_notes

def get_notes_for(msgid):
    full_mail_notes = get_mail_notes()
    for mail_notes in full_mail_notes:
        if mail_notes.msgid == msgid:
            return mail_notes
    return None

def add_note(msgid, line_nr, text):
    full_mail_notes = get_mail_notes()
    notes_list = [n for n in full_mail_notes if n.msgid == msgid]
    if len(notes_list) == 0:
        notes = Notes(msgid, {})
        full_mail_notes.append(notes)
    else:
        notes = notes_list[0]
    if not line_nr in notes.line_notes:
        notes.line_notes[line_nr] = []
    note = Note(text=text)
    notes.line_notes[line_nr].append(note)
    write_mail_notes_file(full_mail_notes)

def remove_notes(msgid, line_nr, indices):
    deleted = False
    full_mail_notes = get_mail_notes()
    for notes_idx, notes in enumerate(full_mail_notes):
        if notes.msgid != msgid:
            continue
        if not line_nr in notes.line_notes:
            return 'no note for the line number'
        line_notes = notes.line_notes[line_nr]
        indices.sort(reverse=True)
        if len(line_notes) < indices[0] + 1:
            return 'too high index'
        for idx in indices:
            del line_notes[idx]

        if len(line_notes) == 0:
            del notes.line_notes[line_nr]
        if len(notes.line_notes) == 0:
            del full_mail_notes[notes_idx]
        deleted = True
        break
    if not deleted:
        return 'No note for the msgid?'

    write_mail_notes_file(full_mail_notes)

def main(args):
    full_mail_notes = get_mail_notes()
    if args.action == 'list':
        if args.msgid is None:
            mail_notes = full_mail_notes
        else:
            mail_notes = get_notes_for(args.msgid)
            if mail_notes is None:
                print('no note for the msgid')
                exit(1)
            mail_notes = [mail_notes]
        for mail_note in mail_notes:
            for line_nr in sorted(mail_note.line_notes.keys()):
                print('%s:%s' % (mail_note.msgid, line_nr))
                notes = mail_note.line_notes[line_nr]
                for idx, note in enumerate(notes):
                    print('- %d: %s' % (idx, note.text))
    elif args.action == 'add':
        add_note(args.msgid, args.line_nr, args.text)
    elif args.action == 'remove':
        err = remove_notes(args.msgid, args.line_nr, [args.note_idx])
        if err is not None:
            print(err)
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
    parser_add.add_argument('line_nr', metavar='<line number>', type=int,
                            help='line number of the mail to add note for')
    parser_add.add_argument('text', metavar='<text>',
                            help='the text note to add')

    parser_remove = subparsers.add_parser('remove', help='remove a note')
    parser_remove.add_argument('msgid', metavar='<message id>',
                               help='message id of mail to add notes for')
    parser_remove.add_argument('line_nr', metavar='<line number>', type=int,
                               help='line number of the mail to add note for')
    parser_remove.add_argument('note_idx', metavar='<note idx>', type=int,
                               help='indices of notes to remove')
