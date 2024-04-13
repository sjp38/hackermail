# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

import _hkml
import hkml_list
import hkml_open

def handle_with_b4(args, mail):
    msgid = mail.get_field('message-id')

    if args.action == 'apply':
        to_return = os.getcwd()
        os.chdir(args.repo)
        rc = subprocess.call(
                ['b4', 'shazam', '--add-link', '--add-my-sob', msgid])
        os.chdir(to_return)
        if rc != 0:
            print('applying the patch series failed')
        return rc

def handle_without_b4(args, mail):
    fd, patch_file = tempfile.mkstemp(prefix='hkml_patch_')
    with open(patch_file, 'w') as f:
        f.write(hkml_open.mail_display_str(mail, False, False))

    if args.action == 'check':
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
        for tag in ['Tested', 'Reviewed', 'Acked']:
            if not line.startswith('%s-by:' % tag):
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

def get_patch_mails(mail, is_cv):
    # Not patchset but single patch
    patch_mails = []
    if get_patch_index(mail) is None:
        return [mail]

    if is_cv is False:
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

    if subprocess.call(['which', 'b4'], stdout=subprocess.DEVNULL) == 0:
        if args.action == 'apply' and args.use_b4 is True:
            return handle_with_b4(args, mail)

    msgid = mail.get_field('message-id')
    mails = hkml_list.last_listed_mails()
    threads = hkml_list.threads_of(mails)
    is_cv = False
    for thread_root_mail in threads:
        mail = find_mail_from_thread(thread_root_mail, msgid) 
        if mail is not None:
            if mail == thread_root_mail:
                is_cv = True
            break
    if mail is None:
        print('cannot find the mail')
        exit(1)

    if not 'patch' in mail.subject_tags:
        print('seems the mail is not patch mail')
        exit(1)

    for patch_mail in get_patch_mails(mail, is_cv):
        handle_without_b4(args, patch_mail)

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
    # Maybe fore some internet disconnected case.
    parser_apply.add_argument('--use_b4', action='store_true',
                              help='use b4')

    parser_check = subparsers.add_parser('check',
                                         help='run a checker for the patch')
    parser_check.add_argument(
            'mail', metavar='<mail>',
            help=' '.join(
                ['The mail to apply as a patch.',
                'Could be index on the list, or \'clipboard\'']))
    parser_check.add_argument('checker', metavar='<program>',
                              help='patch checker program')
