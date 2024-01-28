# SPDX-License-Identifier: GPL-2.0

import os
import json

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

# list of HkmlMonitorRequest objects
requests = None

def get_requests_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'monitor_requests')

def get_requests():
    global requests

    if requests is None:
        requests = []
        requests_file_path = get_requests_file_path()
        if os.path.isfile(requests_file_path):
            with open(requests_file_path, 'r') as f:
                requests = [HkmlMonitorRequest.from_kvpairs(kvp)
                            for kvp in json.load(f)]

    return requests

def write_requests_file():
    requests = get_requests()
    requests_file_path = get_requests_file_path()
    with open(requests_file_path, 'w') as f:
        json.dump([r.to_kvpairs() for r in requests], f, indent=4)

def add_requests(request):
    requests = get_requests()
    requests.append(request)
    write_requests_file()

def remove_requests(name=None, idx=None):
    '''Returns whether removal has success'''
    requests = get_requests()
    if name is not None:
        found = False
        for idx, request in enumerate(requests):
            if request.name == name:
                found = True
                break

    if idx is None and found is False:
        return False
    if idx >= len(idx):
        return False
    del requests[idx]
    write_requests_file()
    return True

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
