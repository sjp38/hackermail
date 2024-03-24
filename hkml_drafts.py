# SPDX-License-Identifier: GPL-2.0

import datetime
import json
import os

import _hkml

def add_draft(draft_file):
    hkml_dir = _hkml.get_hkml_dir()
    drafts_file = os.path.join(hkml_dir, 'drafts.json')
    if not os.path.isfile(drafts_file):
        drafts = []
    else:
        with open(drafts_file, 'r') as f:
            drafts = json.load(f)

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

    with open(drafts_file, 'w') as f:
        json.dump(drafts, f, indent=4)

def main(args):
    if args.action == 'add':
        return add_draft(args.draft)

def set_argparser(parser):
    parser.description = 'manage draft mails'
    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>')

    parser_add = subparsers.add_parser(
            'add', help='add a draft to the drafts list')
    parser_add.add_argument(
            'draft', metavar='<file>', help='file containing the draft mail')
