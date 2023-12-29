import json
import os
import subprocess
import tempfile

import _hkml
import hkml_cache
import hkml_format_reply
import hkml_send

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
    reply_mbox_str = hkml_format_reply.format_reply(mail)
    fd, reply_tmp_path = tempfile.mkstemp(prefix='hkml_reply_')
    with open(reply_tmp_path, 'w') as f:
        f.write(reply_mbox_str)
    if subprocess.call(['vim', reply_tmp_path]) != 0:
        print('editing the reply failed.  The draft is at %s' %
                reply_tmp_path)
        exit(1)
    hkml_send.send_mail(reply_tmp_path, get_confirm=True)
    os.remove(reply_tmp_path)
    return

if __name__ == 'main__':
    main()
