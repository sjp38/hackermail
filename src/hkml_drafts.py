# SPDX-License-Identifier: GPL-2.0

import datetime
import json
import os

import _hkml

def get_drafts():
    hkml_dir = _hkml.get_hkml_dir()
    drafts_file = os.path.join(hkml_dir, 'drafts.json')
    if not os.path.isfile(drafts_file):
        drafts = []
    else:
        with open(drafts_file, 'r') as f:
            drafts = json.load(f)
    return drafts

def store_drafts(drafts):
    hkml_dir = _hkml.get_hkml_dir()
    drafts_file = os.path.join(hkml_dir, 'drafts.json')
    with open(drafts_file, 'w') as f:
        json.dump(drafts, f, indent=4)

def add_draft(draft_file):
    drafts = get_drafts()
    draft = {'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    with open(draft_file, 'r') as f:
        draft_content = f.read()
    draft['content'] = draft_content
    header = draft_content.split('\n\n')[0]
    for line in header.split('\n'):
        if line.startswith('Subject: '):
            subject = line[9:]
            break
    draft['subject'] = subject
    drafts.append(draft)
    drafts.sort(key=lambda x: x['date'])

    store_drafts(drafts)

def list_drafts():
    drafts = get_drafts()
    for idx, draft in enumerate(drafts):
        print('[%d] %s (saved at %s)' % (idx, draft['subject'], draft['date']))

def remove_draft(draft_idx):
    drafts = get_drafts()
    if draft_idx >= len(drafts):
        print('too high index')
        exit(1)
    del drafts[draft_idx]
    store_drafts(drafts)

def open_draft(draft_idx):
    drafts = get_drafts()
    if draft_idx >= len(drafts):
        print('too high index')
        exit(1)
    print(drafts[draft_idx]['content'])

def main(args):
    if args.action == 'add':
        return add_draft(args.draft)
    elif args.action == 'list':
        list_drafts()
        return
    elif args.action == 'remove':
        remove_draft(args.draft)
    elif args.action == 'open':
        open_draft(args.draft)

def set_argparser(parser):
    parser.description = 'manage draft mails'
    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>')

    parser_add = subparsers.add_parser(
            'add', help='add a draft to the drafts list')
    parser_add.add_argument(
            'draft', metavar='<file>', help='file containing the draft mail')

    parser_list = subparsers.add_parser(
            'list', help='list draft mails on the list')

    parser_remove = subparsers.add_parser(
            'remove', help='remove a draft mail from the list')
    parser_remove.add_argument(
            'draft', metavar='<index>', type=int,
            help='index of the draft on the list')

    parser_open = subparsers.add_parser('open', help='read the draft')
    parser_open.add_argument(
            'draft', metavar='<index>', type=int,
            help='index of the draft on the list')

    parser_resume = subparsers.add_parser('resume', help='resume writing')
    parser_resume.add_argument(
            'draft', metavar='<index>', type=int,
            help='index of the draft on the list')
