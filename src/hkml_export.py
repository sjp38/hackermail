# SPDX-License-Identifier: GPL-2.0

import json
import os

import _hkml
import _hkml_list_cache

def export_mails(mails, export_file):
    if export_file[-5:] == '.json':
        with open(export_file, 'w') as f:
            json.dump([m.to_kvpairs() for m in mails], f, indent=4)
        return

    with open(export_file, 'w') as f:
        for mail in mails:
            if mail.mbox is None:
                mail.get_field('message-id')
            f.write('\n'.join(
                ['From hackermail Thu Jan  1 00:00:00 1970', mail.mbox,'']))

def main(args):
    mails = _hkml_list_cache.last_listed_mails()
    if args.range is not None:
        mails = [mail for mail in mails
                 if mail.pridx >= args.range[0] and mail.pridx < args.range[1]]
    return export_mails(mails, args.export_file)

def set_argparser(parser):
    parser.description = 'export mails'
    parser.add_argument(
            'export_file', metavar='<file>',
            help='file to save exported mail (mbox or json)')
    parser.add_argument(
            '--range', nargs=2, metavar=('<start>', '<end>'), type=int,
            help='a half-open range of mails from the list to export')
