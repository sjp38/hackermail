# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

import _hkml
import hkml_list
import hkml_open

def apply_action(args, mail):
    fd, patch_file = tempfile.mkstemp(prefix='hkml_patch_')
    with open(patch_file, 'w') as f:
        f.write(hkml_open.mail_display_str(mail))

    if args.action == 'check':
        if args.checker is None:
            checkpatch = os.path.join('scripts', 'checkpatch.pl')
            if os.path.isfile(checkpatch):
                args.checker = checkpatch
            else:
                print('<cheker> is not given; checkpatch.pl is also not found')
                exit(1)
        print(mail.subject)
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

def get_patch_index(mail):
    tag_end_idx = mail.subject.find(']')
    for field in mail.subject[:tag_end_idx].split():
        idx_total = field.split('/')
        if len(idx_total) != 2:
            continue
        if idx_total[0].isdigit() and idx_total[1].isdigit():
            return int(idx_total[0])
    return None

def find_add_tags(patch_mail, mail_to_check):
    for line in mail_to_check.get_field('body').split('\n'):
        for tag in ['Tested-by:', 'Reviewed-by:', 'Acked-by:', 'Fixes:']:
            if not line.startswith(tag):
                continue
            print('Found below from "%s"' %
                  mail_to_check.get_field('subject'))
            print('    %s' % line)
            answer = input('add the tag to the patch? [Y/n] ')
            if answer.lower() != 'n':
                err = patch_mail.add_tag(line)
                if err is not None:
                    print(err)
    if mail_to_check.replies is None:
        return
    for reply in mail_to_check.replies:
        find_add_tags(patch_mail, reply)

def get_patch_mails(mail, dont_add_cv):
    # Not patchset but single patch
    is_cv = mail.series is not None and mail.series[0] == 0
    patch_mails = []
    if get_patch_index(mail) is None:
        patch_mails = [mail]
    elif is_cv is False:
        patch_mails = [mail]
    else:
        patch_mails += [r for r in mail.replies
                       if 'patch' in r.subject_tags]
    for patch_mail in patch_mails:
        msgid = patch_mail.get_field('message-id')
        if msgid.startswith('<') and msgid.endswith('>'):
            msgid = msgid[1:-1]
        site = _hkml.get_manifest()['site']
        url = '%s/%s' % (site, msgid)
        patch_mail.add_tag('Link: %s' % url)
        if patch_mail.replies is None:
            continue
        for reply in patch_mail.replies:
            find_add_tags(patch_mail, reply)
        user_name = subprocess.check_output(
                ['git', 'config', 'user.name']).decode().strip()
        user_email = subprocess.check_output(
                ['git', 'config', 'user.email']).decode().strip()
        patch_mail.add_tag('Signed-off-by: %s <%s>' % (user_name, user_email))
    patch_mails.sort(key=lambda m: get_patch_index(m))
    if is_cv and dont_add_cv is False:
        print('Given mail seems the cover letter of the patchset.')
        print('Adding the cover letter on the first patch.')
        patch_mails[0].add_cv(mail, len(patch_mails))
    return patch_mails

def find_mail_from_thread(thread, msgid):
    if thread.get_field('message-id') == msgid:
        return thread
    if thread.replies is None:
        return None
    for reply in thread.replies:
        found_mail = find_mail_from_thread(reply, msgid)
        if found_mail is not None:
            return found_mail

def get_mail_with_replies(msgid):
    mails = hkml_list.last_listed_mails()
    threads = hkml_list.threads_of(mails)
    for thread_root_mail in threads:
        mail_with_replies = find_mail_from_thread(thread_root_mail, msgid)
        if mail_with_replies is not None:
            return mail_with_replies

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

    mail = get_mail_with_replies(mail.get_field('message-id'))
    if mail is None:
        print('cannot find the mail')
        exit(1)

    if not 'patch' in mail.subject_tags:
        print('seems the mail is not patch mail')
        exit(1)

    for patch_mail in get_patch_mails(mail, args.dont_add_cv):
        apply_action(args, patch_mail)

def set_argparser(parser):
    parser.description = 'handle patch series mail thread'
    parser.add_argument('--dont_add_cv', action='store_true',
                        help='don\'t add cover letter to first patch')

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
                                         help='run a checker for the patch')
    parser_check.add_argument(
            'mail', metavar='<mail>',
            help=' '.join(
                ['The mail to apply as a patch.',
                'Could be index on the list, or \'clipboard\'']))
    parser_check.add_argument('checker', metavar='<program>', nargs='?',
                              help='patch checker program')
