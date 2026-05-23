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
