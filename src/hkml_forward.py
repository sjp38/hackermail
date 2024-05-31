# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

import _hkml
import hkml_list
import hkml_open
import hkml_write

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

    mail_str = hkml_open.mail_display_str(mail)

    subject = args.subject
    if subject is None:
        subject = 'Fwd: %s' % mail.subject

    mbox = hkml_write.format_mbox(subject, args.in_reply_to, args.to,
                                  args.cc, mail_str, from_=None, draft=None)

    if args.format_only:
        print(mbox)
        return

    fd, tmp_path = tempfile.mkstemp(prefix='hkml_forward_')
    with open(tmp_path, 'w') as f:
        f.write(mbox)
    if subprocess.call(['vim', tmp_path]) != 0:
        print('writing mail with editor failed')
        exit(1)
    with open(tmp_path, 'r') as f:
        mbox = f.read()

    print(mbox)

    answer = input('Will send above mail.  Okay? [y/N] ')
    if answer.lower() != 'y':
        answer = input('Save the mail as a file for later update? [Y/n] ')
        if answer.lower() != 'n':
            print('The mail is saved at %s' % tmp_path)
            return
        os.remove(tmp_path)
        return
    _hkml.cmd_str_output(['git', 'send-email', tmp_path])

def set_argparser(parser):
    parser.description = 'forward a mail'
    parser.add_argument(
            'mail', metavar='<mail>',
            help=' '.join(
                ['The mail to forward.',
                'Could be index on the list, or \'clipboard\'']))
    parser.add_argument('--subject', metavar='<subject>', type=str,
            help='Subject of the mail.')
    parser.add_argument('--in-reply-to', metavar='<message id>',
            help='Add in-reply-to field in the mail header')
    parser.add_argument('--to', metavar='<email address>', nargs='+',
            help='recipients of the mail')
    parser.add_argument('--cc', metavar='<email address>', nargs='+',
            help='cc recipients of the mail')
    parser.add_argument('--format_only', action='store_true',
            help='print formatted mail template only')

