import json
import os

import _hkml
import hkml_cache
import hkml_list

def set_argparser(parser):
    parser.add_argument(
            'mail_idx', metavar='<index>', type=int,
            help='index of the mail to reply to')

def main(args=None):
    if not args:
        parser = argparser.ArgumentParser()
        set_Argparser(parser)
        args = parser.parse_args()

    with open(os.path.join(_hkml.get_hkml_dir(), 'mail_idx_to_cache_key'),
              'r') as f:
        key = json.load(f)['%d' % args.mail_idx]
    mail = hkml_cache.get_mail(key=key)
    if mail is None:
        print('mail is not cached')
        exit(1)
    lines = []
    hkml_list.pr_mail_content(mail, False, False, lines)
    hkml_list.write_send_reply('\n'.join(lines))

if __name__ == 'main__':
    main()
