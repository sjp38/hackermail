# SPDX-License-Identifier: GPL-2.0

import _hkml
import hkml_monitor_add

class HkmlMonitorRequest:
    mailing_lists = None
    sender_keywords = None
    subject_keywords = None
    body_keywords = None
    thread_of_msgid = None

    noti_mails = None
    noti_files = None
    noti_interval = None

    monitor_interval = None

    name = None

    def __init__(self, mailing_lists, sender_keywords, subject_keywords,
                 body_keywords, thread_of_msgid, noti_mails, noti_files,
                 noti_interval, monitor_interval, name):
        self.mailing_lists = mailing_lists
        self.sender_keywords = sender_keywords
        self.subject_keywords = subject_keywords
        self.body_keywords = body_keywords
        self.thread_of_msgid = thread_of_msgid
        self.noti_mails = noti_mails
        self.noti_files = noti_files
        self.noti_interval = noti_interval
        self.monitor_interval = monitor_interval
        self.name = name

    def to_kvpairs(self):
        return vars(self)

    @classmethod
    def from_kvpairs(cls, kvpairs):
        self = cls()
        for key, value in kvpairs.items():
            setattr(self, key, value)

def set_argparser(parser):
    _hkml.set_manifest_option(parser)
    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>')

    parser_add = subparsers.add_parser('add', help='add a monitoring request')
    hkml_monitor_add.set_argparser(parser_add)

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
        hkml_monitor_add.main(args)
    elif args.action == 'remove':
        print('remove monitor query')
