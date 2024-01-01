# SPDX-License-Identifier: GPL-2.0

import json
import os
import subprocess
import tempfile

import _hkml
import hkml_cache
import hkml_list
import hkml_send
import hkml_write

def format_reply(mail):
    subject = mail.get_field('subject')
    if subject and subject.split()[0].lower() != 're:':
        subject = 'Re: %s' % subject

    in_reply_to = mail.get_field('message-id')
    cc = [x for x in [mail.get_field('to'), mail.get_field('cc')] if x]
    to = [mail.get_field('from')]

    body_lines = []
    date = mail.get_field('date')
    if date and to[0]:
        body_lines.append('On %s %s wrote:' % (date, to[0]))
        body_lines.append('')
    body = mail.get_field('body')
    for line in body.split('\n'):
        body_lines.append('> %s' % line)
    body = '\n'.join(body_lines)

    return hkml_write.format_mbox(subject, in_reply_to, to, cc, body)

def set_argparser(parser):
    parser.add_argument(
            'mail_idx', metavar='<index>', type=int,
            help='index of the mail to reply to')
    parser.add_argument(
            '--format_only', action='store_true',
            help='print formatted reply template only')

def main(args=None):
    if not args:
        parser = argparser.ArgumentParser()
        set_Argparser(parser)
        args = parser.parse_args()

    key = hkml_list.get_mail_cache_key(args.mail_idx)
    mail = hkml_cache.get_mail(key=key)
    if mail is None:
        print('mail is not cached')
        exit(1)
    reply_mbox_str = format_reply(mail)
    if args.format_only:
        print(reply_mbox_str)
        return

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
