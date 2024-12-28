# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

import _hkml
import _hkml_list_cache
import hkml_list
import hkml_open
import hkml_patch_format

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

def check_patches(checker, patch_files, patch_mails, first_patch_is_cv):
    if checker is None:
        checkpatch = os.path.join('scripts', 'checkpatch.pl')
        if os.path.isfile(checkpatch):
            checker = checkpatch
        else:
            return '<cheker> is not given; checkpatch.pl is also not found'

    nr_complained_patches = 0
    for idx, patch_file in enumerate(patch_files):
        if idx == 0 and first_patch_is_cv:
            continue
        print(patch_mails[idx].subject)
        rc = subprocess.call([checker, patch_file])
        if rc != 0:
            nr_complained_patches += 1
    print('%d complained patches found' % nr_complained_patches)
    # cleanup tempoeral patches only when success, to let investigation easy
    rm_tmp_patch_dir(patch_files)
    return None

def apply_patches(patch_files, first_patch_is_cv, repo):
    for idx, patch_file in enumerate(patch_files):
        if idx == 0 and first_patch_is_cv:
            continue
        rc = subprocess.call(['git', '-C', repo, 'am', patch_file])
        if rc != 0:
            return 'applying patch (%s) failed' % patch_file
    # cleanup tempoeral patches only when success, to let investigation easy
    rm_tmp_patch_dir(patch_files)
    return None

def move_patches(patch_files, dest_dir):
    if len(patch_files) == 0:
        print('no patch to export')
    saved_dir = os.path.dirname(patch_files[-1])
    if dest_dir is not None:
        for patch_file in patch_files:
            basename = os.path.basename(patch_file)
            os.rename(patch_file, os.path.join(dest_dir, basename))
        os.rmdir(saved_dir)
        saved_dir = dest_dir
    print('\npatch files are saved at \'%s\'\n' % saved_dir)

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

def rm_tmp_patch_dir(patch_files):
    dirname = os.path.dirname(patch_files[-1])
    for patch_file in patch_files:
        os.remove(patch_file)
    os.rmdir(dirname)

def apply_action_to_mails(mail, args):
    err_to_return = None
    patch_mails = get_patch_mails(mail, args.dont_add_cv)
    patch_files, err = write_patch_mails(patch_mails)
    if err is not None:
        return 'writing patch files failed (%s)' % err

    first_patch_is_cv = False
    if len(patch_mails) > 0:
        first_patch_is_cv = is_cover_letter(patch_mails[0])

    if args.action == 'check':
        return check_patches(
                args.checker, patch_files, patch_mails, first_patch_is_cv)
    elif args.action == 'apply':
        return apply_patches(patch_files, first_patch_is_cv, args.repo)
    elif args.action == 'export':
        move_patches(patch_files, args.export_dir)
        return None

def review_patches(args):
    patch_files = args.patch_files
    for patch_file in patch_files:
        patch_mail = _hkml.read_mbox_file(patch_file)[0]
        print(hkml_open.mail_display_str(patch_mail, valid_mbox=True, recipients_per_line=True))

def main(args):
    if args.action == 'format':
        return hkml_patch_format.main(args)
    elif args.action == 'review':
        return review_patches(args)

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
    hkml_patch_format.set_argparser(parser_format)

    parser_review = subparsers.add_parser(
            'review', help='review patch files before sending')
    parser_review.add_argument('patch_files', metavar='<file>', nargs='+',
                               help='patch files to review')
