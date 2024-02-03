# SPDX-License-Identifier: GPL-2.0

import copy
import datetime
import json
import math
import os
import tempfile
import time

import _hkml
import hkml_list
import hkml_monitor_add
import hkml_thread
import hkml_write

class HkmlMonitorRequest:
    mailing_lists = None
    mail_list_filter = None

    noti_mails = None
    noti_files = None

    monitor_interval = None

    name = None

    def __init__(self, mailing_lists, mail_list_filter,
                 noti_mails, noti_files, monitor_interval, name):
        self.mailing_lists = mailing_lists
        self.mail_list_filter = mail_list_filter
        self.noti_mails = noti_mails
        self.noti_files = noti_files
        self.monitor_interval = monitor_interval
        self.name = name

    def to_kvpairs(self):
        kvpairs = copy.deepcopy(vars(self))
        kvpairs['mail_list_filter'] = self.mail_list_filter.to_kvpairs()
        return {k: v for k, v in kvpairs.items() if v is not None}

    @classmethod
    def from_kvpairs(cls, kvpairs):
        self = cls(*[None] * 6)
        for key, value in kvpairs.items():
            if key == 'mail_list_filter':
                continue
            setattr(self, key, value)

        self.mail_list_filter = hkml_list.MailListFilter.from_kvpairs(
                kvpairs['mail_list_filter'])
        return self

    def __str__(self):
        return json.dumps(self.to_kvpairs(), indent=4, sort_keys=True)

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

def pr_w_time(text):
    '''Print text with timestamp'''
    print('[%s] %s' %
          (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), text))

def mail_in(mail, mails):
    for m in mails:
        if m.get_field('message-id') == mail.get_field('message-id'):
            return True
    return False

def get_mails_to_check(request, ignore_mails_before, last_monitored_mails):
    mails_to_check = []
    for mailing_list in request.mailing_lists:
        if not mailing_list in last_monitored_mails:
            last_monitored_mails[mailing_list] = None
        last_mail = last_monitored_mails[mailing_list]
        if last_mail is None:
            since = ignore_mails_before
            commits_range = None
        else:
            since = None
            commits_range = '%s..' % last_mail.gitid

        fetched_mails = hkml_list.get_mails(
                source=mailing_list, fetch=True, manifest=None,
                since=since, until=None, min_nr_mails=None, max_nr_mails=None,
                commits_range=commits_range)
        if len(fetched_mails) > 0:
            last_monitored_mails[mailing_list] = fetched_mails[-1]
        mails_to_check += fetched_mails
    return mails_to_check

def get_mails_to_noti(mails_to_check, request):
    mails_to_noti = []

    for mail in mails_to_check:
        if request.mail_list_filter.should_filter_out(mail):
            continue

        mails_to_noti.append(mail)

    return mails_to_noti

def format_noti_text(request, mails_to_noti):
    show_lore_link = _hkml.get_manifest(
            None)['site'] == 'https://lore.kernel.org'
    lines = [
            'monitor result noti at %s' % datetime.datetime.now(),
            'monitor request',
            '%s' % request,
            '',
            ]

    lines.append(hkml_list.mails_to_str(
        mails_to_noti, mails_filter=None, show_stat=True, show_thread_of=None,
        descend=True, sort_threads_by=['first_date'], collapse_threads=False,
        show_lore_link=show_lore_link, nr_cols=80, runtime_profile=[],
        show_runtime_profile=False))
    noti_text = '\n'.join(lines)
    return noti_text

def do_monitor(request, ignore_mails_before, last_monitored_mails):
    mails_to_check = get_mails_to_check(request, ignore_mails_before,
                                        last_monitored_mails)
    mails_to_noti = get_mails_to_noti(mails_to_check, request)

    print('%d mails to noti' % len(mails_to_noti))
    if len(mails_to_noti) == 0:
        print('request was')
        print('%s' % request)
        return

    noti_text = format_noti_text(request, mails_to_noti)

    print('#')
    print('# noti text start')
    print(noti_text)
    print('# noti text end')
    print('#')

    if request.noti_files is not None:
        for file in request.noti_files:
            lines = []
            if os.path.isfile(file):
                with open(file, 'r') as f:
                    lines.append(f.read())
            with open(file, 'w') as f:
                f.write('\n'.join(lines + [noti_text]))

    if request.noti_mails is not None:
        mail_content = '\n'.join([
                'Subject: [hkml-noti] for monitor request %s' % request.name,
                '',
                noti_text])
        fd, tmp_path = tempfile.mkstemp(prefix='hkml_monitor_')
        with open(tmp_path, 'w') as f:
            f.write(mail_content)

        cmd = ['git', 'send-email', tmp_path, '--to'] + request.noti_mails
        _hkml.cmd_str_output(['git', 'send-email', tmp_path,
                              '--to'] + request.noti_mails)
        os.remove(tmp_path)

def get_monitor_stop_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'monitor_stop')

def start_monitoring(ignore_mails_before):
    requests = get_requests()
    monitor_interval_gcd = math.gcd(*[r.monitor_interval for r in requests])

    last_monitor_time = [None] * len(requests)
    last_monitored_mails = []
    for i in range(len(requests)):
        last_monitored_mails.append({})

    while not os.path.isfile(get_monitor_stop_file_path()):
        for idx, req in enumerate(requests):
            last_monitor = last_monitor_time[idx]
            now = time.time()
            if (last_monitor is None or
                now - last_monitor >= req.monitor_interval):
                do_monitor(req, ignore_mails_before, last_monitored_mails[idx])

                last_monitor_time[idx] = now
        pr_w_time('sleep %d seconds' % monitor_interval_gcd)
        time.sleep(monitor_interval_gcd)

    os.remove(get_monitor_stop_file_path())

def stop_monitoring():
    with open(get_monitor_stop_file_path(), 'w') as f:
        f.write('issued at %s' % datetime.datetime.now())

def main(args):
    if args.action == 'add':
        hkml_monitor_add.main(args)
    elif args.action == 'status':
        for idx, request in enumerate(get_requests()):
            print('request %d' % idx)
            print('%s' % request)
    elif args.action == 'remove':
        if args.request.isdigit():
            if remove_requests(idx=int(args.request)) is False:
                print('failed removing the request')
        else:
            if remove_requests(name=args.request) is False:
                print('failed removing the request')
    elif args.action == 'start':
        if args.ignore_mails_before is None:
            ignore_mails_before = datetime.datetime.now()
        else:
            try:
                ignore_mails_before = datetime.datetime.strptime(
                        args.ignore_mails_before, '%Y-%m-%d %H:%M:%S')
            except:
                print('parsing --ignore_mails_before failed')
                print('the argument should be in \'%Y-%m-%d %H:%M:%S\' format')
                exit(1)

        start_monitoring(ignore_mails_before)
    elif args.action == 'stop':
        stop_monitoring()

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
    parser_start.add_argument(
            '--ignore_mails_before', metavar='<%Y-%m-%d %H:%M:%S>',
            help='Ignore monitoring target mails that sent before this time')

    parser_stop = subparsers.add_parser(
            'stop', help='stop monitoring')
