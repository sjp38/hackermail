# SPDX-License-Identifier: GPL-2.0

import json
import os

import _hkml
import hkml_cache
import hkml_list

def export_mails(mails, export_file):
    if export_file[-5:] != '.mbox':
        with open(export_file, 'w') as f:
            json.dump([m.to_kvpairs() for m in mails], f, indent=4)
        return

    with open(export_file, 'w') as f:
        for mail in mails:
            if mail.mbox is None:
                mail.get_field('message-id')
            f.write('\n'.join(
                ['From mboxrd@z Thu Jan  1 00:00:00 1970', mail.mbox,'']))

def set_argparser(parser):
    parser.add_argument(
            'export_file', metavar='<file>',
            help='file to save exported mail (mbox or json)')
    parser.add_argument(
            '--range', nargs=2, metavar=('<start>', '<end>'), type=int,
            help='a half-open range of mails from the list to export')

def main(args=None):
    if args is None:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    idx_to_cache_keys = hkml_list.get_last_mail_idx_key_cache()
    idxs = [int(idx) for idx in idx_to_cache_keys.keys()]
    if args.range is not None:
        idxs = [idx for idx in idxs
                if idx >= args.range[0] and idx < args.range[1]]
    mails = []
    for idx in idxs:
        key = idx_to_cache_keys['%d' % idx]
        mail = hkml_cache.get_mail(key=key)
        if mail is None:
            print('warning: %d-th mail seems not cached, cannot export'
                  % idx)
            continue
        mails.append(mail)
    return export_mails(mails, args.export_file)

if __name__ == '__main__':
    main()
