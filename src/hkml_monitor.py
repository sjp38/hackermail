# SPDX-License-Identifier: GPL-2.0

import copy
import datetime
import json
import math
import os
import sys
import tempfile
import time

import _hkml
import hkml_list


class HkmlMonitorRequest:
    mailing_lists = None
    mail_list_filter = None
    mail_list_decorator = None

    noti_mails = None
    noti_files = None

    monitor_interval = None

    name = None

    def __init__(
        self,
        mailing_lists,
        mail_list_filter,
        mail_list_decorator,
        noti_mails,
        noti_files,
        monitor_interval,
        name,
    ):
        self.mailing_lists = mailing_lists
        self.mail_list_filter = mail_list_filter
        self.mail_list_decorator = mail_list_decorator
        self.noti_mails = noti_mails
        self.noti_files = noti_files
        self.monitor_interval = monitor_interval
        self.name = name

    def to_kvpairs(self):
        kvpairs = copy.deepcopy(vars(self))
        kvpairs["mail_list_filter"] = self.mail_list_filter.to_kvpairs()
        kvpairs["mail_list_decorator"] = self.mail_list_decorator.to_kvpairs()
        return {k: v for k, v in kvpairs.items() if v is not None}

    def set_mail_list_decorator_from_kvpairs(self, kvpairs):
        if kvpairs is None:
            list_decorator = hkml_list.MailListDecorator(None)
            list_decorator.show_stat = True
            list_decorator.ascend = False
            list_decorator.sort_threads_by = ["first_date"]
            list_decorator.collapse = False
            list_decorator.show_url = (
                _hkml.get_manifest()["site"] == "https://lore.kernel.org"
            )
            list_decorator.show_runtime_profile = False
            self.mail_list_decorator = list_decorator
            return
        self.mail_list_decorator = hkml_list.MailListDecorator.from_kvpairs(kvpairs)

    @classmethod
    def from_kvpairs(cls, kvpairs):
        self = cls(*[None] * 7)
        for key, value in kvpairs.items():
            if key in ["mail_list_filter", "mail_list_decorator"]:
                continue
            setattr(self, key, value)

        self.mail_list_filter = hkml_list.MailListFilter.from_kvpairs(
            kvpairs["mail_list_filter"]
        )
        self.set_mail_list_decorator_from_kvpairs(
            kvpairs["mail_list_decorator"] if "mail_list_decorator" in kvpairs else None
        )
        return self

    def __str__(self):
        return json.dumps(self.to_kvpairs(), indent=4, sort_keys=True)


# list of HkmlMonitorRequest objects
requests = None


def get_requests_file_path():
    return os.path.join(_hkml.get_hkml_dir(), "monitor_requests")


def get_requests():
    global requests

    if requests is None:
        requests = []
        requests_file_path = get_requests_file_path()
        if os.path.isfile(requests_file_path):
            with open(requests_file_path, "r") as f:
                requests = [
                    HkmlMonitorRequest.from_kvpairs(kvp) for kvp in json.load(f)
                ]

    return requests


def write_requests_file():
    requests = get_requests()
    requests_file_path = get_requests_file_path()
    with open(requests_file_path, "w") as f:
        json.dump([r.to_kvpairs() for r in requests], f, indent=4)


def add_requests(request):
    requests = get_requests()
    requests.append(request)
    write_requests_file()


def remove_requests(name=None, idx=None):
    """Returns whether removal has success"""
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
    """Print text with timestamp"""
    print("[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text))


def mail_in(mail, mails):
    for m in mails:
        if m.get_field("message-id") == mail.get_field("message-id"):
            return True
    return False


def get_mails_to_check(request, ignore_mails_before, last_monitored_mails):
    mails_to_check = []
    msgids = {}
    for mailing_list in request.mailing_lists:
        if not mailing_list in last_monitored_mails:
            last_monitored_mails[mailing_list] = None
        last_mail = last_monitored_mails[mailing_list]
        if last_mail is None:
            since = ignore_mails_before
            commits_range = None
        else:
            since = None
            commits_range = "%s.." % last_mail.gitid

        fetched_mails, err = hkml_list.get_mails(
            source=mailing_list,
            fetch=True,
            since=since,
            until=None,
            min_nr_mails=None,
            max_nr_mails=None,
            commits_range=commits_range,
        )
        if err is not None:
            print("hkml_list.get_mails() failed (%s)" % err)
            return []
        if len(fetched_mails) > 0:
            last_monitored_mails[mailing_list] = fetched_mails[-1]
        for mail in fetched_mails:
            msgid = mail.get_field("message-id")
            if not msgid in msgids:
                mails_to_check.append(mail)
            msgids[msgid] = True
    return mails_to_check


def get_mails_to_noti(mails_to_check, request):
    mails_to_noti = []

    for mail in mails_to_check:
        if request.mail_list_filter.should_filter_out(mail):
            continue

        mails_to_noti.append(mail)

    return mails_to_noti


def format_noti_text(request, mails_to_noti):
    lines = [
        "monitor result noti at %s" % datetime.datetime.now(),
        "monitor request",
        "%s" % request,
        "",
    ]

    list_decorator = request.mail_list_decorator

    list_data, err = hkml_list.mails_to_list_data(
        mails_to_noti,
        do_find_ancestors_from_cache=False,
        mails_filter=None,
        list_decorator=list_decorator,
        show_thread_of=None,
        runtime_profile=[],
        stat_only=False,
        stat_authors=False,
    )
    if err is not None:
        return "mails_to_list_data() fail (%s)" % err
    lines.append(list_data.text)
    noti_text = "\n".join(lines)
    return noti_text


def do_monitor(request, ignore_mails_before, last_monitored_mails):
    mails_to_check = get_mails_to_check(
        request, ignore_mails_before, last_monitored_mails
    )
    mails_to_noti = get_mails_to_noti(mails_to_check, request)

    print("%d mails to noti" % len(mails_to_noti))
    if len(mails_to_noti) == 0:
        print("request was")
        print("%s" % request)
        return

    noti_text = format_noti_text(request, mails_to_noti)

    print("#")
    print("# noti text start")
    print(noti_text)
    print("# noti text end")
    print("#")

    if request.noti_files is not None:
        for file in request.noti_files:
            lines = []
            if os.path.isfile(file):
                with open(file, "r") as f:
                    lines.append(f.read())
            with open(file, "w") as f:
                f.write("\n".join(lines + [noti_text]))

    if request.noti_mails is not None:
        mail_content = "\n".join(
            [
                "Subject: [hkml-noti] for monitor request %s" % request.name,
                "",
                noti_text,
            ]
        )
        fd, tmp_path = tempfile.mkstemp(prefix="hkml_monitor_")
        with open(tmp_path, "w") as f:
            f.write(mail_content)

        _hkml.cmd_str_output(
            [
                "git",
                "send-email",
                tmp_path,
                "--8bit-encoding=UTF-8",
                "--confirm",
                "never",
                "--to",
            ]
            + request.noti_mails
        )
        os.remove(tmp_path)


def get_monitor_stop_file_path():
    return os.path.join(_hkml.get_hkml_dir(), "monitor_stop")


def start_monitoring(ignore_mails_before):
    requests = get_requests()

    # math.gcd() supports arbitrary number of positional args starting from
    # Python 3.9.  Support lower versions.

    monitor_interval_gcd = requests[0].monitor_interval
    for r in requests[1:]:
        monitor_interval_gcd = math.gcd(monitor_interval_gcd, r.monitor_interval)
    if monitor_interval_gcd < 60:
        print("<60 seconds monitoring interval is too short!")
        return 1

    last_monitor_time = [None] * len(requests)
    last_monitored_mails = []
    for i in range(len(requests)):
        last_monitored_mails.append({})

    while not os.path.isfile(get_monitor_stop_file_path()):
        for idx, req in enumerate(requests):
            last_monitor = last_monitor_time[idx]
            now = time.time()
            if last_monitor is None or now - last_monitor >= req.monitor_interval:
                do_monitor(req, ignore_mails_before, last_monitored_mails[idx])

                last_monitor_time[idx] = now
        pr_w_time("sleep %d seconds" % monitor_interval_gcd)
        time.sleep(monitor_interval_gcd)

    os.remove(get_monitor_stop_file_path())
    return 0


def stop_monitoring():
    with open(get_monitor_stop_file_path(), "w") as f:
        f.write("issued at %s" % datetime.datetime.now())


def main(args):
    if args.action == "add":
        add_requests(
            HkmlMonitorRequest(
                args.mailing_lists,
                hkml_list.MailListFilter(args),
                hkml_list.MailListDecorator(args),
                args.noti_mails,
                args.noti_files,
                args.monitor_interval,
                args.name,
            )
        )
    elif args.action == "status":
        for idx, request in enumerate(get_requests()):
            print("request %d" % idx)
            print("%s" % request)
    elif args.action == "remove":
        if args.request.isdigit():
            if remove_requests(idx=int(args.request)) is False:
                print("failed removing the request")
        else:
            if remove_requests(name=args.request) is False:
                print("failed removing the request")
    elif args.action == "start":
        if args.since is None:
            ignore_mails_before = datetime.datetime.now()
        else:
            try:
                ignore_mails_before = datetime.datetime.strptime(args.since, "%Y-%m-%d")
            except:
                try:
                    ignore_mails_before = datetime.datetime.strptime(
                        args.since, "%Y-%m-%d %H:%M:%S"
                    )
                except:
                    print("parsing --since failed")
                    print(
                        " ".join(
                            [
                                "the argument should be in '%Y-%m-%d'",
                                "or '%Y-%m-%d %H:%M:%S' format",
                            ]
                        )
                    )
                    exit(1)

        return start_monitoring(ignore_mails_before)
    elif args.action == "stop":
        stop_monitoring()


def set_add_arguments(parser):
    parser.add_argument(
        "mailing_lists",
        nargs="+",
        metavar="<mailing list>",
        help="monitoring target mailing lists",
    )

    hkml_list.add_mails_filter_arguments(parser)
    hkml_list.add_decoration_arguments(parser, show_help=True)

    parser.add_argument(
        "--noti_mails",
        nargs="+",
        metavar="<email address>",
        help="mail addresses to send monitoring results notification",
    )
    parser.add_argument(
        "--noti_files",
        nargs="+",
        metavar="<file>",
        help="file paths to write monitoring results notification",
    )
    parser.add_argument(
        "--monitor_interval",
        type=int,
        metavar="<seconds>",
        default=300,
        help="do monitoring once per this time interval",
    )
    parser.add_argument("--name", metavar="<name>", help="name of the request")


def set_argparser(parser):
    _hkml.set_manifest_option(parser)
    if sys.version_info >= (3, 7):
        subparsers = parser.add_subparsers(
            title="action", dest="action", metavar="<action>", required=True
        )
    else:
        subparsers = parser.add_subparsers(
            title="action", dest="action", metavar="<action>"
        )

    parser_add = subparsers.add_parser("add", help="add a monitoring request")
    set_add_arguments(parser_add)

    parser_remove = subparsers.add_parser(
        "remove", help="remove a given monitoring request"
    )
    parser_remove.add_argument(
        "request",
        metavar="<index or name>",
        help="name or index of the request to remove",
    )

    parser_status = subparsers.add_parser(
        "status", help="show monitoring status including requests"
    )

    parser_start = subparsers.add_parser("start", help="start monitoring")
    parser_start.add_argument(
        "--since",
        metavar="<%Y-%m-%d[ %H:%M:%S]>",
        help="Ignore monitoring target mails that sent before this time",
    )

    parser_stop = subparsers.add_parser("stop", help="stop monitoring")
