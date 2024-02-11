# SPDX-License-Identifier: GPL-2.0

def main(args):
    print(args)

def set_argparser(parser):
    parser.description = 'manage tags of mails'
    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>')

    parser_add = subparsers.add_parser('add', help='add tags to a mail')
    parser_add.add_argument(
            'mail_idx', metavar='<index>',
            help='index of the mail to add tags')
    parser_add.add_argument(
            'tags', metavar='<string>', nargs='+',
            help='tags to add to the mail')

    parser_remove = subparsers.add_parser('remove', help='remove tags from a mail')
    parser_remove.add_argument(
            'mail_idx', metavar='<index>',
            help='index of the mail to remove tags')
    parser_remove.add_argument(
            'tags', metavar='<string>', nargs='+',
            help='tags to remove from the mail')

    parser_list = subparsers.add_parser('list', help='list tags')
