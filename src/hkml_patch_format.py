# SPDX-License-Identifier: GPL-2.0

import os
import subprocess

import _hkml
import hkml_open
import hkml_patch

def add_patch_recipients(patch_file, to, cc):
    mail = _hkml.read_mbox_file(patch_file)[0]
    mail.add_recipients('to', to)
    mail.add_recipients('cc', cc)
    to_write = hkml_open.mail_display_str(
            mail, head_columns=80, valid_mbox=True, recipients_per_line=True)
    with open(patch_file, 'w') as f:
        f.write(to_write)

def is_linux_tree(dir):
    try:
        # 1da177e4c3f41524e886b7f1b8a0c1fc7321cac2 is the initial commit of
        # Linux' git-era.
        output = subprocess.check_output(
                ['git', '-C', dir, 'log', '--pretty=%s',
                 '1da177e4c3f41524e886b7f1b8a0c1fc7321cac2']).decode()
    except:
        return False
    return output.strip() == 'Linux-2.6.12-rc2'

def is_kunit_patch(patch_file):
    # kunit maintainers willing to be Cc-ed for any kunit tests.  But kunit
    # tests are spread over tree, and therefore MAINTAINERS file cannot handle
    # it always.  Add some additional rules here.

    # damon kunit tests are at mm/damon/tests/
    if 'mm/damon/tests' in patch_file:
        return True
    # most kunit test files are assumed to be named with kunit suffix.
    if 'kunit' in patch_file:
        return True
    return False

def find_linux_patch_recipients(patch_file):
    if not os.path.exists('./scripts/get_maintainer.pl'):
        return []
    cmd = ['./scripts/get_maintainer.pl', '--nogit', '--nogit-fallback',
           '--norolestats']
    recipients = subprocess.check_output(
            cmd + [patch_file]).decode().strip().split('\n')
    recipients = [r for r in recipients if r != '']
    if is_kunit_patch(patch_file):
        recipients += ['Brendan Higgins <brendan.higgins@linux.dev>',
               'David Gow <davidgow@google.com>',
               'kunit-dev@googlegroups.com',
               'linux-kselftest@vger.kernel.org']
    return recipients

def add_patches_recipients(patch_files, to, cc, first_patch_is_cv,
                           on_linux_tree):
    if on_linux_tree and os.path.exists('./scripts/get_maintainer.pl'):
        print('get_maintainer.pl found.  add recipients using it.')

    total_cc = [] + cc
    cc_for_patches = {}
    for idx, patch_file in enumerate(patch_files):
        if first_patch_is_cv and idx == 0:
            continue
        if on_linux_tree:
            linux_cc = find_linux_patch_recipients(patch_file)
            total_cc += linux_cc
        else:
            linux_cc = []
        patch_cc = sorted(list(set(cc + linux_cc)))
        cc_for_patches[patch_file] = patch_cc
    if first_patch_is_cv:
        total_cc = sorted(list(set(total_cc)))
        cc_for_patches[patch_files[0]] = total_cc

    if len(to) == 0:
        print('You did not set --to, and we will set below as Cc:')
        for idx, recipient in enumerate(total_cc):
            print('%d. %s' % (idx, recipient))
        answer = input(
                'Shall I set one of above as To: for all mails? [N/index] ')
        try:
            to = [total_cc[int(answer)]]
        except:
            to = []
    for patch_file in patch_files:
        patch_cc = cc_for_patches[patch_file]
        for t in to:
            if t in patch_cc:
                patch_cc.remove(t)
        add_patch_recipients(patch_file, to, patch_cc)

def add_base_commit_as_cv(patch_file, commits):
    base_commit = commits.split('..')[0]
    cv_draft = '\n'.join([
        '',
        "*** below is the commit message of %s." % base_commit,
        "*** 'hkml patch format' assumes it as a draft of this",
        "*** cover letter, and hence pasted it here.",
        '***',
        '*** if this only bothers you, report the issue.',
        '',
        subprocess.check_output(
            ['git', 'log', '-1', '--pretty=%b', base_commit]).decode()])
    with open(patch_file, 'r') as f:
        cv_orig_content = f.read()
    cv_orig_paragraphs = cv_orig_content.split('\n\n')
    cv_content = '\n\n'.join(
            [cv_orig_paragraphs[0], cv_draft] + cv_orig_paragraphs[1:])
    with open(patch_file, 'w') as f:
        f.write(cv_content)

def main(args):
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

    on_linux_tree = is_linux_tree('./')
    add_patches_recipients(patch_files, args.to, args.cc, add_cv,
                           on_linux_tree)

    if add_cv:
        add_base_commit_as_cv(patch_files[0], args.commits)

    if on_linux_tree and os.path.exists('./scripts/checkpatch.pl'):
        print('checkpatch.pl found.  shall I run it?')
        print('(hint: you can do this manually via \'hkml patch check\')')
        answer = input('[Y/n] ')
        if answer.lower() != 'n':
            hkml_patch.check_patches(
                    './scripts/checkpatch.pl', patch_files, None,
                    rm_patches=False)

    print('would you review recipients of formatted patches?')
    print('(hint: you can do this manually via \'hkml patch recipients\')')
    answer = input('[Y/n] ')
    if answer.lower() != 'n':
        hkml_patch.list_recipients(patch_files)

def set_argparser(parser):
    parser.add_argument('commits', metavar='<commits>',
                        help='commits to convert to patch files')
    parser.add_argument('-o', '--output_dir', metavar='<dir>', default='./',
                        help='directory to save formatted patch files')
    parser.add_argument('--rfc', action='store_true',
                        help='mark as RFC patches')
    parser.add_argument('--subject_prefix', metavar='<string>',
                        help='subject prefix')
    parser.add_argument('--to', metavar='<recipient>', nargs='+',
                        default=[],
                        help='To: recipients')
    parser.add_argument('--cc', metavar='<recipient>', nargs='+',
                        default=[],
                        help='Cc: recipients')
