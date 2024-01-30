# SPDX-License-Identifier: GPL-2.0

import hkml_list
import hkml_monitor

def main(args):
    if args.thread_of is not None:
        mail = hkml_list.get_mail(args.thread_of)
        thread_of_msgid = mail.get_field('message-id')
    else:
        thread_of_msgid = None

    hkml_monitor.add_requests(
            hkml_monitor.HkmlMonitorRequest(
                args.mailing_lists, args.sender, args.subject, args.body,
                thread_of_msgid, args.noti_mails, args.noti_files,
                args.monitor_interval, args.name))

def set_argparser(parser):
    parser.add_argument(
            'mailing_lists', nargs='+', metavar='<mailing list>',
            help='monitoring target mailing lists')
    parser.add_argument(
            '--sender', nargs='+', metavar='<keyword>',
            help='monitoring target keywords in senders of mails')
    parser.add_argument(
            '--subject', nargs='+', metavar='<keyword>',
            help='monitoring target keywords in subjects of mails')
    parser.add_argument(
            '--body', nargs='+', metavar='<keyword>',
            help='monitoring target keywords in bodies of mails')
    parser.add_argument(
            '--thread_of', metavar='<mail id>', type=int,
            help='any mail in monitoring target threads')
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
