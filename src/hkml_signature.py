# SPDX-License-Identifier: GPL-2.0

import json
import os
import subprocess
import sys
import tempfile

import _hkml
import hkml_write

'''
The file is a json format, having a list of strings.
'''
def signatures_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'signatures')

def read_signatures_file():
    if not os.path.isfile(signatures_file_path()):
        return ['Sent using hkml (https://github.com/sjp38/hackermail)']
    with open(signatures_file_path(), 'r') as f:
        return json.load(f)

def write_signatures_file(signatures):
    with open(signatures_file_path(), 'w') as f:
        json.dump(signatures, f, indent=4)

def add_signature():
    fd, tmp_path = tempfile.mkstemp(prefix='hkml_signature_')
    with open(tmp_path, 'w') as f:
        f.write('\n'.join([
            '',
            '# Please enter the signature you want to add.',
            '# Lines starting with "#" will be ignored.']))
    err = hkml_write.open_editor(tmp_path, 'signature')
    if err is not None:
        print(err)
        exit(1)
    with open(tmp_path, 'r') as f:
        lines = []
        for line in f:
            if line.startswith('#'):
                continue
            lines.append(line.strip())
        signature = '\n'.join(lines)
    os.remove(tmp_path)
    signatures = read_signatures_file()
    signatures.append(signature)
    write_signatures_file(signatures)
    return

def edit_signature(signature_idx):
    signatures = read_signatures_file()
    signature = signatures[signature_idx]
    fd, tmp_path = tempfile.mkstemp(prefix='hkml_signature_')
    with open(tmp_path, 'w') as f:
        f.write('\n'.join([
            signature,
            '',
            '# Please edit the signature above as you want.',
            '# Lines starting with "#" will be ignored.']))
    hkml_write.open_editor(tmp_path, 'signature')
    with open(tmp_path, 'r') as f:
        lines = []
        for line in f:
            if line.startswith('#'):
                continue
            lines.append(line.strip())
        signature = '\n'.join(lines)
    os.remove(tmp_path)
    signatures[signature_idx] = signature
    write_signatures_file(signatures)

def number_suffix(n):
    if n % 100 in (11, 12, 13):
        return 'th'
    elif n % 10 == 1:
        return 'st'
    elif n % 10 == 2:
        return 'nd'
    elif n % 10 == 3:
        return 'rd'
    else:
        return 'th'

def main(args):
    if args.action == 'list':
        signatures = read_signatures_file()
        for idx, signature in enumerate(signatures):
            print('%d%s signature' % (idx, number_suffix(idx)))
            print('```')
            print(signature)
            print('```')
    elif args.action == 'add':
        add_signature()
    elif args.action == 'edit':
        edit_signature(args.signature_idx)
    elif args.action == 'remove':
        signatures = read_signatures_file()
        del signatures[args.signature_idx]
        write_signatures_file(signatures)

def set_argparser(parser):
    parser.description = 'manage signature for mails'
    if sys.version_info >= (3,8):
        subparsers = parser.add_subparsers(
                title='action', dest='action', metavar='<action>', required=True)
    else:
        subparsers = parser.add_subparsers(
                title='action', dest='action', metavar='<action>')

    parser_add = subparsers.add_parser('add', help='add a signature')
    parser_list = subparsers.add_parser('list', help='list signatures')
    parser_edit = subparsers.add_parser('edit', help='edit a signature')
    parser_edit.add_argument(
            'signature_idx', metavar='<index>', type=int,
            help='index of the signature from the "list" output')
    parser_remove = subparsers.add_parser('remove', help='remove signature')
    parser_remove.add_argument(
            'signature_idx', metavar='<index>', type=int,
            help='index of the signature from the "list" output')
    parser.epilog = ' '.join([
        'If any signature exists,',
        'hkml will add those on mail drafts with instructions.',
        ])
