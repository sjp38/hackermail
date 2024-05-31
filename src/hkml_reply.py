# SPDX-License-Identifier: GPL-2.0

import json
import os
import subprocess
import tempfile

import _hkml
import hkml_list
import hkml_send
import hkml_write

def format_reply(mail, attach_file):
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
    return hkml_write.format_mbox(subject, in_reply_to, to, cc, body,
                                  from_=None, draft=None,
                                  attach_files=attach_file)

def main(args):
    if args.mail.isdigit():
        mail = hkml_list.get_mail(int(args.mail))
    elif args.mail == 'clipboard':
        mails, err = _hkml.read_mails_from_clipboard()
        if err != None:
            print('reading mails in clipboard failed: %s' % err)
            exit(1)
        if len(mails) != 1:
            print('multiple mails in clipboard')
            exit(1)
        mail = mails[0]
    else:
        print('unsupported <mail> (%s)' % args.mail)

    if mail is None:
        print('mail is not cached')
        exit(1)
    reply_mbox_str = format_reply(mail, args.attach)
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

def set_argparser(parser):
    parser.description = 'reply to a mail'
    parser.add_argument(
            'mail', metavar='<mail>',
            help=' '.join(
                ['The mail to reply to.',
                'Could be index on the list, or \'clipboard\'']))
    hkml_write.add_common_arguments(parser)
