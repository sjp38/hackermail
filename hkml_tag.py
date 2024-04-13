# SPDX-License-Identifier: GPL-2.0

import json
import os

import _hkml
import hkml_list
import hkml_sync

'''
Tags information is saved in a json file called 'tags' under the hkml
directory.

The data structure is a map.  Keys are msgid of mails.  Values are map having
keys 'mail' and 'tags'.  'mail' is _hkml.Mail.to_kvpairs() output of the mail
of the message id.  'tags' is a list of tags for the mail.
'''

def tag_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'tags')

def read_tags_file():
    if not os.path.isfile(tag_file_path()):
        return {}
    with open(tag_file_path(), 'r') as f:
        return json.load(f)

def write_tags_file(tags):
    with open(tag_file_path(), 'w') as f:
        json.dump(tags, f, indent=4)
    if hkml_sync.syncup_ready():
        answer = input('Tags updated.  Sync? [Y/n] ')
        if answer.lower() != 'n':
            hkml_sync.syncup(_hkml.get_hkml_dir(), remote=None)

def mails_of_tag(tag):
    tags_map = read_tags_file()
    mails = []
    for msgid in tags_map:
        tags = tags_map[msgid]['tags']
        if tag in tags:
            mails.append(_hkml.Mail(kvpairs=tags_map[msgid]['mail']))
    return mails

def do_add_tags(mail, tags):
    msgid = mail.get_field('message-id')

    tags_map = read_tags_file()
    if not msgid in tags_map:
        tags_map[msgid] = {'mail': mail.to_kvpairs(), 'tags': tags}
    else:
        existing_tags = tags_map[msgid]['tags']
        for tag in tags:
            if not tag in existing_tags:
                existing_tags.append(tag)
    write_tags_file(tags_map)

def add_tags(mail_idx, tags):
    mail = hkml_list.get_mail(mail_idx)
    if mail is None:
        print('failed getting mail of the index.  Maybe wrong index?')
        exit(1)

    do_add_tags(mail, tags)

def remove_tags(mail_idx, tags):
    mail = hkml_list.get_mail(mail_idx)
    if mail is None:
        print('failed getting mail of the index.  Maybe wrong index?')
        exit(1)

    msgid = mail.get_field('message-id')

    tags_map = read_tags_file()
    if not msgid in tags_map:
        print('seems the index is wrong, or having no tag')
        exit(1)
    existing_tags = tags_map[msgid]['tags']
    for tag in tags:
        if not tag in existing_tags:
            print('the mail is not having the tag')
            exit(1)
        existing_tags.remove(tag)
    write_tags_file(tags_map)

def get_tag_nr_mails():
    '''
    Return dict having tags as key, numbers of mails of the tag as value
    '''
    tag_nr_mails = {}
    tags_map = read_tags_file()
    for msgid in tags_map:
        for tag in tags_map[msgid]['tags']:
            if not tag in tag_nr_mails:
                tag_nr_mails[tag] = 0
            tag_nr_mails[tag] += 1
    return tag_nr_mails

def tag_exists(tagname):
    return tagname in get_tag_nr_mails()

def list_tags():
    for tag, nr_mails in get_tag_nr_mails().items():
        print('%s: %d mails' % (tag, nr_mails))

def main(args):
    if args.action == 'add':
        return add_tags(args.mail_idx, args.tags)
    elif args.action == 'remove':
        if args.mail_idx is None and len(args.mails) == 0:
            print('mail to remove tags are not specified')
            exit(1)
        if args.mail_idx is not None:
            args.mails.append(args.mail_idx)
        for mail_idx in args.mails:
            remove_tags(mail_idx, args.tags)
        return
    elif args.action == 'list':
        return list_tags()

def set_argparser(parser):
    parser.description = 'manage tags of mails'
    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>')

    parser_add = subparsers.add_parser('add', help='add tags to a mail')
    parser_add.add_argument(
            'mail_idx', metavar='<index>', type=int,
            help='index of the mail to add tags')
    parser_add.add_argument(
            'tags', metavar='<string>', nargs='+',
            help='tags to add to the mail')

    parser_remove = subparsers.add_parser(
            'remove', help='remove tags from a mail')
    parser_remove.add_argument(
            'mail_idx', metavar='<index>', type=int, nargs='?',
            help='index of the mail to remove tags')
    parser_remove.add_argument(
            'tags', metavar='<string>', nargs='+',
            help='tags to remove from the mail')
    parser_remove.add_argument('--mails', metavar='<index>', type=int,
                               nargs='+', default=[],
                               help='indexes of the mails to remove tags')

    parser_list = subparsers.add_parser('list', help='list tags')
