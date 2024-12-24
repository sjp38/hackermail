# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

import _hkml
import _hkml_list_cache
import hkml_list
import hkml_open

def apply_action(args, mail, patch_file):
    if args.action == 'check':
        if is_cover_letter(mail):
            return None
        if args.checker is None:
            checkpatch = os.path.join('scripts', 'checkpatch.pl')
            if os.path.isfile(checkpatch):
                args.checker = checkpatch
            else:
                return '<cheker> is not given; checkpatch.pl is also not found'
        print(mail.subject)
        rc = subprocess.call([args.checker, patch_file])
        if rc != 0:
            return 'checker complains something'

    if args.action == 'apply':
        if is_cover_letter(mail):
            return None
        rc = subprocess.call(['git', '-C', args.repo, 'am', patch_file])
        if rc != 0:
            return 'applying patch (%s) failed' % patch_file

    if args.action == 'export':
        print('patch file for mail \'%s\' is saved at \'%s\'' %
              (mail.subject, patch_file))

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

def is_cover_letter(mail):
    return mail.series is not None and mail.series[0] == 0

def get_patch_mails(mail, dont_add_cv):
    patch_mails = [mail]
    is_cv = is_cover_letter(mail)
    if is_cv is True:
        if dont_add_cv == 'ask':
            answer = input('Add cover letter to first patch? [Y/n] ')
            if answer.lower() != 'n':
                dont_add_cv = False
            else:
                dont_add_cv = True

        patch_mails += [r for r in mail.replies
                       if 'patch' in r.subject_tags]
    use_patch_msgid_link = None
    for patch_mail in patch_mails:
        msgid = patch_mail.get_field('message-id')
        if msgid.startswith('<') and msgid.endswith('>'):
            msgid = msgid[1:-1]
        site = _hkml.get_manifest()['site']
        url = '%s/%s' % (site, msgid)
        if use_patch_msgid_link is None and site == 'https://lore.kernel.org':
            answer = input(
                    'use patch.msgid.link domain for patch origin? [Y/n] ')
            use_patch_msgid_link = answer.lower() != 'n'
        if use_patch_msgid_link is True:
            url = 'https://patch.msgid.link/%s' % msgid
        patch_mail.add_tag('Link: %s' % url)
        if patch_mail.replies is None:
            continue
        if is_cover_letter(patch_mail):
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
        patch_mails[1].add_cv(mail, len(patch_mails) - 1)
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
    mails = _hkml_list_cache.last_listed_mails()
    threads = hkml_list.threads_of(mails)
    for thread_root_mail in threads:
        mail_with_replies = find_mail_from_thread(thread_root_mail, msgid)
        if mail_with_replies is not None:
            return mail_with_replies

def write_patch_mails(patch_mails):
    if len(patch_mails) > 9999:
        return None, '>9999 patches'
    files = []
    temp_dir = tempfile.mkdtemp(prefix='hkml_patch_')
    # give index 0 to only coverletter
    if is_cover_letter(patch_mails[0]):
        idx_offset = 0
    else:
        idx_offset = 1
    for idx, mail in enumerate(patch_mails):
        file_name_words = ['%04d-' % (idx + idx_offset)]
        subject = mail.subject.lower()
        # exclude [PATCH ...] like suffix
        tag_closing_idx = subject.find(']')
        subject = subject[tag_closing_idx + 1:]
        for c in subject:
            if not c.isalpha() and not c.isdigit():
                # avoid multiple '-' in the name
                if file_name_words[-1][-1] == '-':
                    continue
                c = '-'
            file_name_words.append(c)
        file_name_words.append('.patch')
        file_name = ''.join(file_name_words)
        file_name = os.path.join(temp_dir, file_name)
        with open(file_name, 'w') as f:
            f.write(hkml_open.mail_display_str(
                mail, head_columns=None, valid_mbox=True))
        files.append(file_name)
    return files, None

def apply_action_to_mails(mail, args):
    err_to_return = None
    patch_mails = get_patch_mails(mail, args.dont_add_cv)
    patch_files, err = write_patch_mails(patch_mails)
    if err is not None:
        return 'writing patch files failed (%s)' % err

    for idx in range(len(patch_mails)):
        err = apply_action(args, patch_mails[idx], patch_files[idx])
        if err is not None:
            err_to_return = err

    if (err_to_return is None and args.action == 'export' and
            len(patch_files) > 0):
        saved_dir = os.path.dirname(patch_files[-1])
        if args.export_dir is not None:
            for patch_file in patch_files:
                basename = os.path.basename(patch_file)
                os.rename(patch_file, os.path.join(args.export_dir, basename))
            os.rmdir(saved_dir)
            saved_dir = args.export_dir
        print('\npatch files are saved at \'%s\'\n' % saved_dir)

    if err_to_return is None and args.action != 'export':
        dirname = os.path.dirname(patch_files[-1])
        for patch_file in patch_files:
            os.remove(patch_file)
        os.rmdir(dirname)

    return err_to_return

def add_recipients(patch_file, to, cc):
    print('add recipients to %s' % patch_file)
    print('\n'.join([' to: %s' % r for r in to]))
    print('\n'.join([' cc: %s' % r for r in cc]))

    mail = _hkml.read_mbox_file(patch_file)[0]
    mail.add_recipients('to', to)
    mail.add_recipients('cc', cc)
    to_write = hkml_open.mail_display_str(mail, head_columns=80,
                                          valid_mbox=True,
                                          recipients_per_line=True)
    with open(patch_file, 'w') as f:
        f.write(to_write)

def add_maintainers(patch_files, first_patch_is_cv):
    total_to = []
    total_cc = []
    cmd = ['./scripts/get_maintainer.pl', '--nogit', '--nogit-fallback',
           '--norolestats']
    for idx, patch_file in enumerate(patch_files):
        if first_patch_is_cv and idx == 0:
            continue
        to = subprocess.check_output(
                cmd + ['--nol', patch_file]).decode().strip().split('\n')
        to = [t for t in to if t != '']
        total_to += to
        cc = subprocess.check_output(
                cmd + ['--nom', patch_file]).decode().strip().split('\n')
        cc = [c for c in cc if c != '']
        total_cc += cc
        add_recipients(patch_file, to, cc)
    if first_patch_is_cv:
        to = sorted(set(total_to))
        cc = sorted(set(total_cc))
        add_recipients(patch_files[0], to, cc)

def add_user_set_recipients(patch_files, to, cc):
    for patch_file in patch_files:
        add_recipients(patch_file, to, cc)

def add_base_commit_as_cv(patch_file, commits):
    base_commit = commits.split('..')[0]
    cv_content = subprocess.check_output(
            ['git', 'log', '-1', '--pretty=%B', base_commit]).decode()
    with open(patch_file, 'a') as f:
        f.write(cv_content)

def format_patches(args):
    commit_ids = subprocess.check_output(
            ['git', 'log', '--pretty=%h', args.commits]
            ).decode().strip().split('\n')
    if len(commit_ids) > 1:
        add_cv = True
    else:
        add_cv = False
    cmd = ['git', 'format-patch', args.commits, '-o', args.output_dir]
    if add_cv:
        cmd.append('--cover-letter')
    if args.subject_prefix is not None:
        cmd.append('--subject-prefix=%s' % args.subject_prefix)
    elif args.rfc is True:
        cmd.append('--rfc')
    patch_files = subprocess.check_output(cmd).decode().strip().split('\n')

    add_user_set_recipients(patch_files, args.to, args.cc)

    if os.path.exists('./scripts/get_maintainer.pl'):
        print('get_maintainer.pl found.  add recipients using it.')
        add_maintainers(patch_files, add_cv)

    if add_cv:
        add_base_commit_as_cv(patch_files[0], args.commits)

    if os.path.exists('./scripts/checkpatch.pl'):
        print('\ncheckpatch.pl found.  run it.')
        for patch_file in patch_files:
            subprocess.call(['./scripts/checkpatch.pl', patch_file])

def main(args):
    if args.action == 'format':
        format_patches(args)
        return

    # For call from hkml_view_mail
    if type(args.mail) is _hkml.Mail:
        mail = args.mail
    elif args.mail.isdigit():
        mail = _hkml_list_cache.get_mail(int(args.mail))
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

    err = apply_action_to_mails(mail, args)
    if err is not None:
        print(err)
        exit(1)

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

    parser_export = subparsers.add_parser('export', help='save as patch files')
    parser_export.add_argument(
            'mail', metavar='<mail>',
            help=' '.join(
                ['The mail to apply as a patch.',
                'Could be index on the list, or \'clipboard\'']))
    parser_export.add_argument('--export_dir', metavar='<dir>',
                               help='directory to save the patch files')

    parser_format = subparsers.add_parser('format', help='format patch files')
    parser_format.add_argument('commits', metavar='<commits>',
                               help='commits to convert to patch files')
    parser_format.add_argument(
            'output_dir', metavar='<dir>', default='./', nargs='?',
            help='directory to save formatted patch files')
    parser_format.add_argument('--rfc', action='store_true',
                               help='mark as RFC patches')
    parser_format.add_argument('--subject_prefix', metavar='<string>',
                               help='subject prefix')
    parser_format.add_argument('--to', metavar='<recipient>', nargs='+',
                               default=[],
                               help='To: recipients')
    parser_format.add_argument('--cc', metavar='<recipient>', nargs='+',
                               default=[],
                               help='Cc: recipients')
