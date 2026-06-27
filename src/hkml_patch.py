# SPDX-License-Identifier: GPL-2.0

import os
import shutil
import subprocess
import sys
import tempfile

import _hkml
import _hkml_list_cache
import _hkml_sashiko_dev
import hkml_list
import hkml_open
import hkml_patch_format
import hkml_reply
import hkml_write
import hkml_send

class Patch:
    mail = None
    collected_patch_tags = None
    cv_text = None
    additional_to = None
    additional_cc = None

    def __init__(self, mail):
        self.mail = mail
        self.collected_patch_tags = {}  # {tag: [val]}
        self.cv_text = None
        self.additional_to = []
        self.additional_cc = []

    def format_tags_par(self, orig_tags_par):
        if len(self.collected_patch_tags) == 0:
            return orig_tags_par, None
        tags = {}
        orig_tag_lines = orig_tags_par.split('\n')
        for tag_line in orig_tag_lines:
            fields = tag_line.split()
            if len(fields) < 2:
                return None, 'invalid tag line (%s)' % tag_line
            tag = fields[0]
            val = ' '.join(fields[1:])
            if not tag in tags:
                tags[tag] = []
            tags[tag].append(val)

        for tag in self.collected_patch_tags:
            if not tag in tags:
                tags[tag] = []
            tags[tag].append(val)

        tag_lines = []
        first_tags = ['Link:', 'Fixes:', 'Reported-by:', 'Closes:', 'Cc:']
        for tag in first_tags:
            if not tag in tags:
                continue
            for val in tags[tag]:
                tag_lines.append('%s %s' % (tag, val))
            del tag_lines[tag]
        last_tags = ['Acked-by:', 'Reviewed-by:', 'Co-developed-by:',
                     'Signed-off-by:']
        for tag in tags:
            if tag in last_tags:
                continue
            for val in tags[tag]:
                tag_lines.append('%s %s' % (tag, val))
        for tag in last_tags:
            for val in tags[tag]:
                tag_lines.append('%s %s' % (tag, val))
        return '\n'.join(tag_lines), None

    def format_str(self):
        '''Returns formatted text and error'''
        mail_text = hkml_open.mail_display_str(
                self.mail, head_columns=None, valid_mbox=True)
        pars = mail_text.split('\n\n')
        additional_header_lines = []
        for recipient in self.additional_to:
            additional_header_lines.append('To: %s' % recipient)
        for recipient in self.additional_cc:
            additional_header_lines.append('Cc: %s' % recipient)
        if len(additional_header_lines) > 0:
            pars[0] += '\n' + '\n'.join(additional_header_lines)

        mail_text = '\n\n'.join(pars)
        three_dash_split = mail_text.split('\n---\n')
        if len(three_dash_split) < 2:
            return None, 'No three dash'
        desc = three_dash_split[0]
        desc_pars = desc.split('\n\n')

        tags_par, err = self.format_tags_par(desc_pars[-1])
        if err is not None:
            return None, 'tags section format fail (%s)' % err
        desc_pars[-1] = tags_par

        desc = '\n\n'.join(desc_pars)
        return '\n---\n'.join([desc] + three_dash_split[1:]), None

def find_mail_item_from_thread(mail_item, msgid):
    if mail_item.mail is None:
        return None
    if mail_item.mail.get_field('message-id') == msgid:
        return mail_item
    for reply in mail_item.reply_items:
        found_item = find_mail_item_from_thread(reply, msgid)
        if found_item is not None:
            return found_item
    return None

def get_mail_item_with_replies(msgid):
    list_data = _hkml_list_cache.get_last_list(except_thread=False)
    mail_items = list_data.mail_items
    for item in mail_items:
        item.set_mail()
    thread_items = hkml_list.thread_items_of(
            mail_items, do_find_ancestors_from_cache=False)
    for thread_root_item in thread_items:
        item_with_replies = find_mail_item_from_thread(thread_root_item, msgid)
        if item_with_replies is not None:
            return item_with_replies
    return None

def user_pointed_mail_item(mail_identifier):
    if mail_identifier.isdigit():
        list_data = _hkml_list_cache.get_last_list(except_thread=False)
        mail_items = list_data.mail_items
        mail_idx = int(mail_identifier)
        if mail_idx >= len(mail_items):
            return None, 'out of mail idx'
        mail_item = mail_items[int(mail_identifier)]
    elif mail_identifier == 'clipboard':
        mails, err = _hkml.read_mails_from_clipboard()
        if err != None:
            return None, 'reading mails in clipboard failed: %s' % err
        if len(mails) != 1:
            return None, 'multiple mails in clipboard'
        mail_item = hkml_list.MailListMailItem(
                mail_cache_key=None, mail=mails[0], prdepth=0,
                parent_item=None, added_by_tag=None)
    else:
        return None, 'unsupported <mail> (%s)' % mail_identifier

    mail_item.set_mail()
    mail_item = get_mail_item_with_replies(
            mail_item.mail.get_field('message-id'))
    if mail_item is None:
        return None, 'get replies of the mail fail'
    return mail_item, None

def rm_tmp_patch_dir(patch_files):
    dirname = os.path.dirname(patch_files[-1])
    for patch_file in patch_files:
        os.remove(patch_file)
    os.rmdir(dirname)

def check_patches(checker, patch_files, patch_mails, rm_patches):
    if patch_mails is None:
        patch_mails = []
        for patch_file in patch_files:
            patch_mails.append(_hkml.read_mbox_file(patch_file)[0])
    checkpatch = os.path.join('scripts', 'checkpatch.pl')
    if checker is None:
        if os.path.isfile(checkpatch):
            checker = checkpatch
        else:
            return '<checker> is not given; checkpatch.pl is also not found'

    complained_patches = []
    for idx, patch_file in enumerate(patch_files):
        try:
            output = subprocess.check_output([checker, patch_file]).decode()
            if checker == checkpatch:
                last_par = output.split('\n\n')[-1]
                if not 'and is ready for submission.' in last_par:
                    raise Exception('checkpatch.pl output seems wrong')
        except Exception as e:
            print('[!!!] %s complained by %s (%s)' % (
                patch_mails[idx].subject, checker, e))
            subprocess.call([checker, patch_file])
            print()
            complained_patches.append(patch_file)
    print('Below %d patches may have problems' % len(complained_patches))
    for patch_file in complained_patches:
        print(' - %s' % patch_file)

    if rm_patches:
        rm_tmp_patch_dir(patch_files)
    return None

def git_am(patch_files, repo):
    for patch_file in patch_files:
        rc = subprocess.call(['git', '-C', repo, 'am', patch_file])
        if rc != 0:
            return 'applying patch (%s) failed' % patch_file
    return None

def add_noff_merge_commit(base_commit, message, git_cmd=['git']):
    final_commit = subprocess.check_output(
            git_cmd + ['rev-parse', 'HEAD']).decode().strip()
    subprocess.call(git_cmd + ['reset', '--hard', base_commit])
    subprocess.call(git_cmd + ['merge', '--no-ff', '--no-edit', final_commit])
    subprocess.call(git_cmd + ['commit', '--amend', '-s', '-m', message])

def git_cherrypick_merge(patch_files, cv_mail, repo):
    git_cmd = ['git', '-C', repo]
    head_commit = subprocess.check_output(
            git_cmd + ['rev-parse', 'HEAD']).decode().strip()
    err = git_am(patch_files[1:], repo)
    if err is not None:
        return err

    cv_merge_msg = '\n'.join([
        'Merge patch series \'%s\'' % cv_mail.subject, '',
        'Below is the cover letter of the series', '',
        cv_mail.get_field('body')])
    add_noff_merge_commit(head_commit, cv_merge_msg, git_cmd)
    return None

def apply_patches(patch_mails, repo):
    err = None

    has_cv = len(patch_mails) > 0 and is_cover_letter(patch_mails[0])
    do_merge = False
    if has_cv:
        print('How should I apply the cover letter?')
        print()
        print('1: add to first patch\'s commit message  # default')
        print('2: add as a bogus baseline commit')
        print('3: add as a merge commit')
        print('4: Ignore it.')
        print()
        answer = input('Enter the number: ')
        try:
            answer = int(answer)
        except:
            pass
        if not answer in [1, 2, 3, 4]:
            answer = 1
        if answer == 1:
            patch_mails[1].add_cv(patch_mails[0], len(patch_mails) - 1)
        elif answer == 2:
            cv_mail = patch_mails[0]
            subject = '==== %s ====' % cv_mail.subject
            content = '%s\n\n%s' % (cv_mail.subject, cv_mail.get_field('body'))
            make_cover_letter_commit(subject, content)
        elif answer == 3:
            do_merge = True

    patch_files, err = write_patch_mails(patch_mails)
    if err is not None:
        return 'writing patch files failed (%s)' % err
    if do_merge:
        err = git_cherrypick_merge(patch_files, patch_mails[0], repo)
    else:
        if has_cv:
            err = git_am(patch_files[1:], repo)
        else:
            err = git_am(patch_files, repo)
    if err is not None:
        return err
    # cleanup tempoeral patches only when success, to let investigation easy
    rm_tmp_patch_dir(patch_files)
    return None

def add_patch_suffix(basename, count):
    patch_sections = basename.split('.')
    suffix = '-' + str(count)
    if len(patch_sections) < 2: # No file extension
        return basename + suffix

    patch_sections[-2] += suffix
    return '.'.join(patch_sections)

def move_patches(patch_files, dest_dir):
    if len(patch_files) == 0:
        print('no patch to export')
    saved_dir = os.path.dirname(patch_files[-1])
    if dest_dir is not None:
        for idx, patch_file in enumerate(patch_files):
            basename = os.path.basename(patch_file)
            new_path = os.path.join(dest_dir, basename)

            # Avoid overwriting existing patches; append -N to the end until
            # the file path is unique
            if (os.path.isfile(new_path)):
                count = 1
                while os.path.isfile(new_path):
                    new_path = os.path.join(dest_dir,
                                            add_patch_suffix(basename, count))
                    count += 1
            shutil.move(patch_file, new_path)
            patch_files[idx] = new_path

        os.rmdir(saved_dir)
        saved_dir = dest_dir
    print('\npatch files are saved at \'%s\' with below names:' % saved_dir)
    for patch_file in patch_files:
        print('- %s' % os.path.basename(patch_file))
    print()

def get_patch_index(mail):
    tag_end_idx = mail.subject.find(']')
    for field in mail.subject[:tag_end_idx].split():
        idx_total = field.split('/')
        if len(idx_total) != 2:
            continue
        if idx_total[0].isdigit() and idx_total[1].isdigit():
            return int(idx_total[0])
    return None

def find_add_tags_item(patch_mail_item, mail_item_to_check):
    for line in mail_item_to_check.mail.get_field('body').split('\n'):
        for tag in ['Tested-by:', 'Reviewed-by:', 'Acked-by:', 'Fixes:',
                    'Cc: stable@', 'Cc: <stable@']:
            if not line.startswith(tag):
                continue
            print('Found below from "%s"' %
                  mail_item_to_check.mail.get_field('subject'))
            print('    %s' % line)
            answer = input('add the tag to the patch? [Y/n] ')
            if answer.lower() != 'n':
                err = patch_mail_item.mail.add_patch_tag(line)
                if err is not None:
                    print(err)
    if mail_item_to_check.reply_items is None:
        return
    for reply in mail_item_to_check.reply_items:
        find_add_tags_item(patch_mail_item, reply)

def is_cover_letter(mail):
    return mail.series is not None and mail.series[0] == 0

def get_link_tag_domain():
    if not _hkml.is_for_lore_kernel_org():
        return None
    site = _hkml.get_manifest()['site']
    print()
    print(' '.join([
        'Should we add Link: tag to the patch?',
        'If so, what domain to use?']))
    print()
    print('1. Yes.  Use https://patch.msgid.link (default)')
    print('2. Yes.  Use %s' % site)
    print('3. No.  Don\'t add Link: tag')
    answer = input('Select: ')
    try:
        answer = int(answer)
    except:
        answer = 1
    if answer == 1:
        return 'https://patch.msgid.link'
    elif answer == 2:
        return site
    else:
        return None

def add_cc_tags_item(patch_mail_item):
    patch_mail = patch_mail_item.mail
    for recipient in recipients_of(patch_mail, 'cc'):
        if recipient == patch_mail.get_field('from'):
            continue
        # add Cc: for formal recipients, e.g., having both name and email
        # address, excluding mailing list.
        if len(recipient.split()) == 1:
            continue
        patch_mail.add_patch_tag('Cc: %s' % recipient)

def get_patch_mail_items(mail_item, dont_add_cv):
    patch_mail_items = [mail_item]
    is_cv = is_cover_letter(mail_item.mail)
    if is_cv is True:
        if dont_add_cv == 'ask':
            answer = input('Add cover letter to first patch? [Y/n] ')
            if answer.lower() != 'n':
                dont_add_cv = False
            else:
                dont_add_cv = True

        patch_mail_items += [
                r for r in mail_item.reply_items
                if 'patch' in r.mail.subject_tags]
    link_domain = get_link_tag_domain()
    for patch_mail_item in patch_mail_items:
        if link_domain is not None:
            msgid = patch_mail_item.mail.get_field('message-id')
            if msgid.startswith('<') and msgid.endswith('>'):
                msgid = msgid[1:-1]
            url = '%s/%s' % (link_domain, msgid)
            err = patch_mail_item.mail.add_patch_tag('Link: %s' % url)
            if err is not None and not is_cover_letter(patch_mail_item.mail):
                return None, 'adding link fail (%s)' % err
        if patch_mail_item.reply_items is None:
            continue
        if is_cover_letter(patch_mail_item.mail):
            continue
        for reply in patch_mail_item.reply_items:
            find_add_tags_item(patch_mail_item, reply)
        add_cc_tags_item(patch_mail_item)
        user_name = subprocess.check_output(
                ['git', 'config', 'user.name']).decode().strip()
        user_email = subprocess.check_output(
                ['git', 'config', 'user.email']).decode().strip()
        err = patch_mail_item.mail.add_patch_tag(
                'Signed-off-by: %s <%s>' % (user_name, user_email))
        if err is not None:
            return None, 'addding s-o-b fail (%s)' % err
    patch_mail_items.sort(key=lambda item: get_patch_index(item.mail))
    if is_cv and dont_add_cv is False:
        print('Given mail seems the cover letter of the patchset.')
        print('Adding the cover letter on the first patch.')
        patch_mail_items[1].mail.add_cv(
                mail_item.mail, len(patch_mail_items) - 1)
    return patch_mail_items, None

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

def check_apply_or_export_item(mail_item, args):
    patch_mail_items, err = get_patch_mail_items(mail_item, args.dont_add_cv)
    if err is not None:
        return 'getting patch mails fail (%s)' % err
    patch_mails = [i.mail for i in patch_mail_items]
    if args.action == 'apply':
        return apply_patches(patch_mails, args.repo)

    patch_files, err = write_patch_mails(patch_mails)
    if err is not None:
        return 'writing patch files failed (%s)' % err

    if args.action == 'check':
        return check_patches(
                args.checker, patch_files, patch_mails, rm_patches=True)
    elif args.action == 'export':
        move_patches(patch_files, args.export_dir)
        return None

def recipients_of(mail, to_cc):
    field = mail.get_field(to_cc)
    if field is None:
        return []
    return [r.strip() for r in field.split(',')]

def common_recipients(patch_mails, to_cc):
    if len(patch_mails) == 0:
        return []
    to_return = []
    for recipient in recipients_of(patch_mails[0], to_cc):
        is_common = True
        for mail in patch_mails[1:]:
            if not recipient in recipients_of(mail, to_cc):
                is_common = False
                break
        if is_common is True:
            to_return.append(recipient)
    return to_return

def list_recipients(patch_files):
    patch_mails = []
    for patch_file in patch_files:
        patch_mails.append(_hkml.read_mbox_file(patch_file)[0])
    common_to = common_recipients(patch_mails, 'to')
    common_cc = common_recipients(patch_mails, 'cc')
    print('Common recipients:')
    for to in common_to:
        print('  To: %s' % to)
    for cc in common_cc:
        print('  Cc: %s' % cc)
    if len(common_to) + len(common_cc) == 0:
        print('  No one')
    for patch_mail in patch_mails:
        exclusive_to = []
        exclusive_cc = []
        for recipient in recipients_of(patch_mail, 'to'):
            if not recipient in common_to:
                exclusive_to.append(recipient)
        for recipient in recipients_of(patch_mail, 'cc'):
            if not recipient in common_cc:
                exclusive_cc.append(recipient)
        if len(exclusive_to + exclusive_cc) > 0:
            print('Additional recipients for "%s"' % patch_mail.subject)
            for to in exclusive_to:
                print('  To: %s' % to)
            for cc in exclusive_cc:
                print('  Cc: %s' % cc)

def is_files_argument(arg):
    if type(arg) is not list:
        return False
    for entry in arg:
        if not os.path.isfile(entry):
            return False
    return True

def make_cover_letter_commit(subject, content=None):
    bogus_dir = 'hkml_cv_bogus'
    if not os.path.isdir(bogus_dir):
        os.mkdir(bogus_dir)
    _, bogus_path = tempfile.mkstemp(prefix='hkml_cv_bogus_', dir=bogus_dir)
    err = subprocess.call(['git', 'add', bogus_path])
    if err:
        print('git add failed')
        return -1
    message = subject
    if content is not None:
        message = '%s\n\n%s' % (message, content)
    return subprocess.call(['git', 'commit', '-s', '-m', message])

def fmt_sashiko_reviews_summary(msgid, for_forwarding=False):
    reviews, err = _hkml_sashiko_dev.get_reviews(msgid)
    if err is not None:
        return None, 'fetching reviews fail (%s)' % err
    lines = []
    if for_forwarding is True:
        lines = [
                'Forwarding sashiko.dev review status for this thread.',
                '',
                '# review url: https://sashiko.dev/#/patchset/%s' % msgid,
                '',
                ]
    if len(reviews) == 0:
        lines.append('zero review')
        return '\n'.join(lines), None
    for review in reviews:
        lines.append('- %s' % review.patch_subject)
        lines.append('  - status: %s' % review.status)
        result = review.result
        if result is not None and result != 'Review completed successfully.':
            lines.append('  - result: %s' % result)
        inline_review =  review.inline_review
        if inline_review is not None and len(inline_review.split('\n')) == 1:
            lines.append('  - review: %s' % inline_review)
        elif inline_review is not None and len(inline_review.split('\n')) > 1:
            lines.append('  - review: ISSUES MAY FOUND')

    lines += [
            '',
            '# hkml [1] generated a draft of this mail.  It can be regenerated',
            '# using below command:',
            '#',
            '#     hkml patch sashiko_dev --thread_status --for_forwarding \\',
            '#             %s' % msgid,
            '#',
            '# [1] https://github.com/sjp38/hackermail',
            ]

    return '\n'.join(lines), None

def fetch_pr_sashiko_reviews(msgid, for_forwarding):
    text, err = fmt_sashiko_reviews_summary(msgid, for_forwarding)
    if err is not None:
        print(err)
        return -1
    print(text)
    return 0

def fmt_sashiko_forward_msg(review):
    msgid = review.patch_msgid
    review_url = 'https://sashiko.dev/#/patchset/%s' % msgid
    print()
    answer = input(
            '\n'.join([
                'Adding your opinion together with the sashiko review sharing',
                'is a recommended practice for reducing traffic.  Will you',
                'do so?  If so, I will adjust format to be easier for that',
                '[Y/n] '
                ]))
    if answer.lower() != 'n':
        reply_form = True
    else:
        reply_form = False

    lines = []
    if reply_form:
        lines += [
                '# sashiko review suggestions',
                '#',
                '# 1. Consider reducing recipients.  Maybe the author,',
                '#    maintainers, reviewers, and mailing list of the',
                '#    direct subsystem and parent susystem mailing lists',
                '#    could be a starting point.',
                '# 2. Add short summary of your opinion at the beginning.',
                '#    For example:',
                '#',
                '#      TL;DR: sashiko found an issue.  I will respin.',
                '#      TL;DR: sashiko found no issue on this patch.',
                '#',
                '# Please DON\'T FORGET removing this comment block before',
                '# sending this!',
                '',
                'Forwarding full sashiko review in a reply format with my ',
                'inline comments below, for sharing details of my view and',
                'doing followup discussions via mails if needed.',
                ]
    else:
        lines.append(
                'Forwarding sashiko review for doing discussions via mails.')
    lines.append('')
    forward_lines = [
        '# review url: %s' % review_url,
        '# start of sashiko.dev inline review',
        '%s' % review.inline_review,
        '# end of sashiko.dev inline review',
        '# review url: %s' % review_url,
        ]
    if reply_form:
        forward_lines = '\n'.join(forward_lines).split('\n')
        reply_lines = ['> %s' % l for l in forward_lines]
        lines += reply_lines
    else:
        lines += forward_lines

    lines += [
            '',
            '# hkml [1] generated a draft of this mail.  You can regenerate',
            '# this using below command:',
            '#',
            '#     hkml patch sashiko_dev --for_forwarding \\',
            '#             %s' % msgid,
            '#',
            '# [1] https://github.com/sjp38/hackermail',
        ]
    return '\n'.join(lines)

def pr_sashiko_for_forwarding(review):
    print(fmt_sashiko_forward_msg(review))

def fetch_pr_sashiko_review(msgid, thread_status, for_forwarding):
    if thread_status is True:
        return fetch_pr_sashiko_reviews(msgid, for_forwarding)
    review, err = _hkml_sashiko_dev.get_review(msgid)
    if err is not None:
        print('fetching review fail (%s)' % err)
        return -1
    if for_forwarding is True:
        return pr_sashiko_for_forwarding(review)

    print('# patch subject: %s' % review.patch_subject)
    print('# patch msgid: %s' % review.patch_msgid)
    print('# review status: %s' % review.status)
    print('# reivew result: %s' % review.result)
    print('# inline review:')
    print(review.inline_review)
    print('# end of sashiko.dev inline review')
    print('# review url: https://sashiko.dev/#/patchset/%s' % msgid)

def forward_sashiko(msgid, thread_status, mail=None):
    if mail is None:
        mails, err = hkml_list.get_thread_mails_from_web(msgid)
        if err is not None:
            print('retrieving mail from web fail (%s)' % err)
            return -1
        mail = None
        for m in mails:
            if m.get_field('message-id') == '<%s>' % msgid:
                mail = m
                break
        if mail is None:
            print('cannot find mail from web-retrieved mails')
            return -1

    orig_subject = mail.get_field('subject')

    if thread_status is True:
        text, err = fmt_sashiko_reviews_summary(msgid, for_forwarding=True)
        if err is not None:
            print(err)
            return -1
        reply_subject = 'Re: (sashiko status) %s' % orig_subject
    else:
        review, err = _hkml_sashiko_dev.get_review(msgid)
        if err is not None:
            print('fetching review fail (%s)' % err)
            return -1
        text = fmt_sashiko_forward_msg(review)
        reply_subject = 'Re: (sashiko review) %s' % orig_subject

    mbox_str = hkml_reply.format_reply(
            mail=mail, attach_file=None, body_lines=[text],
            subject=reply_subject)
    fd, forward_tmp_path = tempfile.mkstemp(prefix='hkml_sashiko_forward_')
    with open(forward_tmp_path, 'w') as f:
        f.write(mbox_str)
    err = hkml_write.open_editor(forward_tmp_path)
    if err is not None:
        print(err)
        return -1
    hkml_send.send_mail(forward_tmp_path, get_confirm=True, erase_mbox=True,
                        orig_draft_subject=None)

def handle_sashiko(msgid, thread_status, for_forwarding, do_forward):
    if do_forward is False:
        return fetch_pr_sashiko_review(msgid, thread_status, for_forwarding)
    return forward_sashiko(msgid, thread_status)

def main(args):
    if args.action == 'format':
        return hkml_patch_format.main(args)
    elif args.action == 'recipients':
        return list_recipients(args.patch_files)
    elif args.action == 'commit_cv':
        if args.as_merge is not None:
            return add_noff_merge_commit(
                    args.as_merge, args.subject, git_cmd=['git'])
        return make_cover_letter_commit(args.subject)
    elif args.action == 'sashiko_dev':
        return handle_sashiko(
                args.msgid, args.thread_status, args.for_forwarding,
                args.forward)

    if args.action == 'check':
        if is_files_argument(args.patch):
            err = check_patches(
                    args.checker, args.patch, None, rm_patches=False)
            if err is not None:
                print(err)
                return 1
            return 0
        elif len(args.patch) > 1:
            print('wrong patch argument')
            return 1
        else:
            args.mail = args.patch[0]

    mail_item, err = user_pointed_mail_item(args.mail)
    if err is not None:
        print(err)
        exit(1)

    err = check_apply_or_export_item(mail_item, args)
    if err is not None:
        print(err)
        exit(1)

def set_argparser(parser):
    parser.description = 'handle patch series mail thread'
    parser.add_argument('--dont_add_cv', action='store_true',
                        help='don\'t add cover letter to first patch')

    if sys.version_info >= (3,7):
        subparsers = parser.add_subparsers(
                title='action', dest='action', metavar='<action>',
                required=True)
    else:
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
            'patch', metavar='<mail or patch file>', nargs='+',
            help=' '.join(
                ['The mail or patch files to check.',
                'In case of a mail, this could be index on the list,',
                 'or \'clipboard\'']))
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

    parser_sashiko = subparsers.add_parser(
            'sashiko_dev', help='fetch and show sashiko.dev review')
    parser_sashiko.add_argument('msgid', metavar='<message id>',
                                help='message id of the patch mail')
    parser_sashiko.add_argument('--thread_status', action='store_true',
                                help='print entire thread review status')
    parser_sashiko.add_argument('--for_forwarding', action='store_true',
                                help='print in mail-forwarding friendly form')
    parser_sashiko.add_argument('--forward', action='store_true',
                                help='forward the sashiko status or review')

    parser_format = subparsers.add_parser('format', help='format patch files')
    hkml_patch_format.set_argparser(parser_format)

    parser_recipients = subparsers.add_parser(
            'recipients', help='show recipients of patch files')
    parser_recipients.add_argument('patch_files', metavar='<file>', nargs='+',
                                   help='the patch files')

    parser_cv_commit = subparsers.add_parser(
            'commit_cv', help='make a commit of cover letter message')
    parser_cv_commit.add_argument('subject', metavar='<subject>',
                                  help='subject of the cover letter commit')
    parser_cv_commit.add_argument('--as_merge', metavar='<base commit>',
                                  help='make it as a no-ff merge commit')
