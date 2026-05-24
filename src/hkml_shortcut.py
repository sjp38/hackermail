# SPDX-License-Identifier: GPL-2.0

'''
$ hkml shortcut list
shortcuts on any view
- 'm': open menu

shortcuts on mails list view
- 'o': open the focused mail
- 'r': reply to the focused mail

shortcuts on text view
- 'r': reply to the mail if it is showing a mail
- 'm': open menu
$
$ hkml shortcut add mails_list f tag foo
$ hkml shortcut add mails_list g untag foo
$ hkml shortcut add mail_view t open_thread_on_line
$ hkml shortcut remove list f
'''

import argparse
import json
import os

import _hkml

class UserConfig:
    category = None
    key_input = None
    action = None
    arguments = None

    def __init__(self, category, key_input, action, arguments):
        self.category = category
        self.key_input = key_input
        self.action = action
        self.arguments = arguments

    def to_kvpairs(self):
        return {
                'category': self.category,
                'key_input': self.key_input,
                'action': self.action,
                'arguments': self.arguments,
                }

    @classmethod
    def from_kvpairs(cls, kvpairs):
        return cls(category=kvpairs['category'],
                   key_input=kvpairs['key_input'], action=kvpairs['action'],
                   arguments=kvpairs['arguments'])

def user_configs_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'shortcut_configs')

def write_user_configs_file(user_configs):
    kvpairs = {
            'configs': [config.to_kvpairs() for config in user_configs],
            }
    with open(user_configs_file_path(), 'w') as f:
        json.dump(kvpairs, f, indent=4, sort_keys=True)

def read_user_configs_file():
    file_path = user_configs_file_path()
    if not os.path.isfile(file_path):
        return []
    with open(file_path, 'r') as f:
        kvpairs = json.load(f)
    return [UserConfig.from_kvpairs(kvp) for kvp in kvpairs['configs']]

def main(args):
    print('not yet implemented')
    return

def set_argparser(parser):
    parser.description = 'handle shortcut on interactive interfaces'

    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>')

    parser_list = subparsers.add_parser('list', help='list shortcuts')

    parser_add = subparsers.add_parser('add', help='add a shortcut')
    parser_add.add_argument(
            'parameter', nargs='+',
            metavar='<categorty> <key input> <action> [argument]...',
            help='add a shortcut')

    parser_remove = subparsers.add_parser('remove', help='remove a shortcut')
    parser_remove.add_argument('category', help='shortcut category')
    parser_remove.add_argument('key_input', help='key input of the shortcut')
