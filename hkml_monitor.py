# SPDX-License-Identifier: GPL-2.0

import datetime
import math
import os
import time
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

    monitor_interval = None

    name = None

    def __init__(self, mailing_lists, sender_keywords, subject_keywords,
                 body_keywords, thread_of_msgid, noti_mails, noti_files,
                 monitor_interval, name):
        self.mailing_lists = mailing_lists
        self.sender_keywords = sender_keywords
        self.subject_keywords = subject_keywords
        self.body_keywords = body_keywords
        self.thread_of_msgid = thread_of_msgid
        self.noti_mails = noti_mails
        self.noti_files = noti_files
        self.monitor_interval = monitor_interval
        self.name = name

    def to_kvpairs(self):
        return vars(self)

    @classmethod
    def from_kvpairs(cls, kvpairs):
        self = cls(*[None] * 9)
        for key, value in kvpairs.items():
            setattr(self, key, value)
        return self

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
        if found is False:
            return False

    if idx >= len(requests):
        return False
    del requests[idx]
    write_requests_file()
    return True

def do_monitor(request):
    print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
          'handle %s' % request)
    pass

def start_monitoring():
    requests = get_requests()
    monitor_interval_gcd = math.gcd(*[r.monitor_interval for r in requests])

    last_monitor_time = [None] * len(requests)

    while True:
        for idx, req in enumerate(requests):
            last_monitor = last_monitor_time[idx]
            now = time.time()
            if (last_monitor is None or
                now - last_monitor >= req.monitor_interval):
                do_monitor(req)
                last_monitor_time[idx] = now
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
              'sleep %d seconds' % monitor_interval_gcd)
        time.sleep(monitor_interval_gcd)

def main(args):
    if args.action == 'add':
        hkml_monitor_add.main(args)
    elif args.action == 'status':
        for idx, request in enumerate(get_requests()):
            print('request %d' % idx)
            print(json.dumps(request.to_kvpairs(), indent=4, sort_keys=True))
    elif args.action == 'remove':
        if args.request.isdigit():
            if remove_requests(idx=int(args.request)) is False:
                print('failed removing the request')
        else:
            if remove_requests(name=args.request) is False:
                print('failed removing the request')
    elif args.action == 'start':
        start_monitoring()

def set_argparser(parser):
    _hkml.set_manifest_option(parser)
    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>')

    parser_add = subparsers.add_parser('add', help='add a monitoring request')
    hkml_monitor_add.set_argparser(parser_add)

    parser_remove = subparsers.add_parser(
            'remove', help='remove a given monitoring request')
    parser_remove.add_argument(
            'request', metavar='<index or name>',
            help='name or index of the request to remove')

    parser_status = subparsers.add_parser(
            'status', help='show monitoring status including requests')

    parser_start = subparsers.add_parser(
            'start', help='start monitoring')

    parser_stop = subparsers.add_parser(
            'stop', help='stop monitoring')
