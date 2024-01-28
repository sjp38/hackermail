# SPDX-License-Identifier: GPL-2.0

def main(args):
    print('add called with %s' % args)

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
            '--thread_of', metavar='<mail id>',
            help='any mail in monitoring target threads')
    parser.add_argument(
            '--noti_mail', nargs='+', metavar='<email address>',
            help='mail addresses to send monitoring results notification')
    parser.add_argument(
            '--noti_file', nargs='+', metavar='<file>',
            help='file paths to write monitoring results notification')
    parser.add_argument(
            '--noti_interval', metavar='<seconds>', type=float,
            help='send notification once per this time interval')
    parser.add_argument(
            '--monitor_interval', type=float, metavar='<seconds>',
            help='do monitoring once per this time interval')
    parser.add_argument(
            '--name', metavar='<name>',
            help='name of the request')
