import json
import os

import _hkml
import hkml_cache

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

    mails = []
    with open(os.path.join(_hkml.get_hkml_dir(), 'mail_idx_to_cache_key'),
              'r') as f:
        to_export = []
        idx_to_cache_keys = json.load(f)
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
    return _hkml.export_mails(mails, args.export_file)

if __name__ == '__main__':
    main()
