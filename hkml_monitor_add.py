# SPDX-License-Identifier: GPL-2.0

import hkml_list
import hkml_monitor

def main(args):
    hkml_monitor.add_requests(
            hkml_monitor.HkmlMonitorRequest(
                args.mailing_lists,
                hkml_list.MailListFilter(args),
                args.noti_mails, args.noti_files,
                args.monitor_interval, args.name))

def set_argparser(parser):
    parser.add_argument(
            'mailing_lists', nargs='+', metavar='<mailing list>',
            help='monitoring target mailing lists')

    hkml_list.add_mails_filter_arguments(parser)

    parser.add_argument(
            '--noti_mails', nargs='+', metavar='<email address>',
            help='mail addresses to send monitoring results notification')
    parser.add_argument(
            '--noti_files', nargs='+', metavar='<file>',
            help='file paths to write monitoring results notification')
    parser.add_argument(
            '--monitor_interval', type=int, metavar='<seconds>', default=300,
            help='do monitoring once per this time interval')
    parser.add_argument(
            '--name', metavar='<name>',
            help='name of the request')
