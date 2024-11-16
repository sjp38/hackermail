# SPDX-License-Identifier: GPL-2.0

import os

import _hkml

'''
The file is a json format, having a list of strings.
'''
def signatures_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'signatures')

def read_signatures_file():
    if not os.path.isfile(signatures_file_path()):
        return []
    with open(signatures_file_path(), 'r') as f:
        return json.load(f)

def write_signatures_file(signatures):
    with open(signatures_file_path(), 'w') as f:
        json.dump(signatures, f, indent=4)

def main(args):
    if args.action == 'list':
        signatures = read_signatures_file()
        for idx, signature in enumerate(signatures):
            print('%d-th signature')
            print('```')
            print(signature)
            print('```')
        return

def set_argparser(parser):
    parser.description = 'manage signature for mails'
    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>')
    parser_add = subparsers.add_parser('add', help='add a signature')
    parser_list = subparsers.add_parser('list', help='list signatures')
    parser_remove = subparsers.add_parser('remove', help='remove signature')
    parser_remove.add_argument(
            'signature_idx', metavar='<index>', type=int, nargs='+',
            help='index of the signature from the "list" output')
