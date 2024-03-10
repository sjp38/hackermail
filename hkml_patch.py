# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

import hkml_list
import hkml_open

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

    fd, patch_file = tempfile.mkstemp(prefix='hkml_patch_')
    with open(patch_file, 'w') as f:
        f.write(hkml_open.mail_display_str(mail, False, False))

    if args.action == 'check':
        rc = subprocess.call([args.checker, patch_file])
        if rc != 0:
            print('checker complains something')
        return rc

    if args.action == 'apply':
        rc = subprocess.call(['git', '-C', args.repo, 'am', patch_file])
        if rc == 0:
            os.remove(patch_file)
        else:
            print('applying patch (%s) failed' % patch_file)

def set_argparser(parser):
    parser.description = 'handle patch series mail thread'
    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>')

    parser_apply = subparsers.add_parser('apply', help='apply the patch')
    parser_apply.add_argument(
            'mail', metavar='<mail>',
            help=' '.join(
                ['The mail to apply as a patch.',
                'Could be index on the list, or \'clipboard\'']))
    parser_apply.add_argument('--repo', metavar='<dir>', default='./',
                              help='git repo to apply the patch')

    parser_check = subparsers.add_parser('check',
                                         help='run checker for the patch')
    parser_check.add_argument(
            'mail', metavar='<mail>',
            help=' '.join(
                ['The mail to apply as a patch.',
                'Could be index on the list, or \'clipboard\'']))
    parser_check.add_argument('checker', metavar='<program>',
                              help='patch checker program to run first')
