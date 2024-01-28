# SPDX-License-Identifier: GPL-2.0

import _hkml

class HkmlMonitorRequest:
    mailing_lists = None
    sender_keywords = None
    subject_keywords = None
    body_keywords = None
    thread_of = None

    notify_send_mail = None
    notify_write_file = None
    notify_frequency = None

def set_argparser(parser):
    _hkml.set_manifest_option(parser)
    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>')

    parser_add = subparsers.add_parser('add', help='add a monitoring request')
    parser_add.add_argument(
            'mailing_lists', nargs='+', metavar='<mailing list>',
            help='monitoring target mailing lists')
    parser_add.add_argument(
            '--sender', nargs='+', metavar='<keyword>',
            help='monitoring target keywords in senders of mails')
    parser_add.add_argument(
            '--subject', nargs='+', metavar='<keyword>',
            help='monitoring target keywords in subjects of mails')
    parser_add.add_argument(
            '--body', nargs='+', metavar='<keyword>',
            help='monitoring target keywords in bodies of mails')
    parser_add.add_argument(
            '--thread_of', metavar='<mail id>',
            help='any mail in monitoring target threads')
    parser_add.add_argument(
            '--noti_mail', nargs='+', metavar='<email address>',
            help='mail addresses to send monitoring results notification')
    parser_add.add_argument(
            '--noti_file', nargs='+', metavar='<file>',
            help='file paths to write monitoring results notification')
    parser_add.add_argument(
            '--noti_interval', metavar='<seconds>', type=float,
            help='send notification once per this time interval')
    parser_add.add_argument(
            '--monitor_interval', type=float, metavar='<seconds>',
            help='do monitoring once per this time interval')

    parser_remove = subparsers.add_parser(
            'remove', help='remove a given monitoring request')
    parser_remove.add_argument('req_index', type=int, metavar='<int>')

    parser_status = subparsers.add_parser(
            'status', help='show monitoring status including requests')

    parser_start = subparsers.add_parser(
            'start', help='start monitoring')

    parser_stop = subparsers.add_parser(
            'stop', help='stop monitoring')

def main(args):
    if args.action == 'add':
        print('add monitor query')
    elif args.action == 'remove':
        print('remove monitor query')
