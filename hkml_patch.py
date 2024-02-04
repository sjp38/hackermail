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

    rc = subprocess.call(['git', '-C', args.repo, 'am', patch_file])
    if rc == 0:
        os.remove(patch_file)
    else:
        print('applying patch (%s) failed' % patch_file)

def set_argparser(parser):
    parser.description = 'apply the mail as a patch on a git repo'
    parser.add_argument(
            'mail', metavar='<mail>',
            help=' '.join(
                ['The mail to apply as a patch.',
                'Could be index on the list, or \'clipboard\'']))
    parser.add_argument('--repo', metavar='<dir>', default='./',
                        help='git repo to apply this patch')
