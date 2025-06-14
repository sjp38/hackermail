# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import sys

import _hkml
import hkml_open
import hkml_patch


def add_patch_recipients(patch_file, to, cc):
    mail = _hkml.read_mbox_file(patch_file)[0]
    mail.add_recipients("to", to)
    mail.add_recipients("cc", cc)
    to_write = hkml_open.mail_display_str(
        mail, head_columns=80, valid_mbox=True, recipients_per_line=True
    )
    with open(patch_file, "w") as f:
        f.write(to_write)


def is_linux_tree(dir):
    try:
        # 1da177e4c3f41524e886b7f1b8a0c1fc7321cac2 is the initial commit of
        # Linux' git-era.
        output = subprocess.check_output(
            [
                "git",
                "-C",
                dir,
                "log",
                "--pretty=%s",
                "1da177e4c3f41524e886b7f1b8a0c1fc7321cac2",
            ],
            stderr=subprocess.DEVNULL,
        ).decode()
    except:
        return False
    return output.strip() == "Linux-2.6.12-rc2"


def is_kunit_patch(patch_file):
    # kunit maintainers willing to be Cc-ed for any kunit tests.  But kunit
    # tests are spread over tree, and therefore MAINTAINERS file cannot handle
    # it always.  Add some additional rules here.

    # damon kunit tests are at mm/damon/tests/
    if "mm/damon/tests" in patch_file:
        return True
    # most kunit test files are assumed to be named with kunit suffix.
    if "kunit" in patch_file:
        return True
    return False


def linux_maintainers_of(patch_or_source_file):
    cmd = [
        "./scripts/get_maintainer.pl",
        "--nogit",
        "--nogit-fallback",
        "--norolestats",
        patch_or_source_file,
    ]
    try:
        recipients = subprocess.check_output(cmd).decode().strip().split("\n")
    except Exception as e:
        return None, "%s fail" % (" ".join(cmd))

    return [r for r in recipients if r != ""], None


def find_linux_patch_recipients(patch_file):
    if not os.path.exists("./scripts/get_maintainer.pl"):
        return [], None
    recipients, err = linux_maintainers_of(patch_file)
    if err is not None:
        return [], err
    if is_kunit_patch(patch_file):
        recipients += [
            "Brendan Higgins <brendan.higgins@linux.dev>",
            "David Gow <davidgow@google.com>",
            "kunit-dev@googlegroups.com",
            "linux-kselftest@vger.kernel.org",
        ]
    return recipients, None


def handle_special_recipients(recipients):
    handled = []
    for r in recipients:
        if os.path.exists(r):
            maintainers, err = linux_maintainers_of(r)
            if err is None:
                handled += maintainers
            else:
                return None, err
        else:
            handled.append(r)
    return handled, None


def get_patch_tag_cc(patch_file):
    cc_list = []
    with open(patch_file, "r") as f:
        txt = f.read()
    pars = txt.split("---")
    if len(pars) < 2:
        return cc_list
    tags_par = pars[0].split("\n\n")[-1]
    for line in tags_par.split("\n"):
        if line.startswith("Cc: "):
            cc_list.append(" ".join(line.split()[1:]))
    return cc_list


def add_patches_recipients(patch_files, to, cc, first_patch_is_cv, on_linux_tree):
    to, err = handle_special_recipients(to)
    if err is not None:
        return err
    cc, err = handle_special_recipients(cc)
    if err is not None:
        return err
    if on_linux_tree and os.path.exists("./scripts/get_maintainer.pl"):
        print("get_maintainer.pl found.  add recipients using it.")

    total_cc = [] + cc
    cc_for_patches = {}
    for idx, patch_file in enumerate(patch_files):
        if first_patch_is_cv and idx == 0:
            continue
        if on_linux_tree:
            linux_cc, err = find_linux_patch_recipients(patch_file)
            if err is not None:
                return err
            total_cc += linux_cc
        else:
            linux_cc = []
        patch_tag_cc = get_patch_tag_cc(patch_file)
        total_cc += patch_tag_cc
        patch_cc = sorted(list(set(cc + linux_cc + patch_tag_cc)))
        cc_for_patches[patch_file] = patch_cc
    if first_patch_is_cv:
        total_cc = sorted(list(set(total_cc)))
        cc_for_patches[patch_files[0]] = total_cc

    if len(to) == 0 and len(total_cc) > 0:
        print("\nYou did not set --to, and we will set below as Cc:")
        for idx, recipient in enumerate(total_cc):
            print("%d. %s" % (idx, recipient))
        answer = input("Shall I set one of above as To: for all mails? [N/index/q] ")
        if answer == "q":
            return "user request quit"
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


def fillup_cv(patch_file, subject, content):
    print("I will do below to the coverletter (%s)" % patch_file)
    print('- replace "*** SUBJECT HERE ***" with')
    print()
    print("    %s" % subject)
    print()
    print('- replace "*** BLURB HERE ***" with')
    content_lines = content.split("\n")
    preview_lines = []
    if len(content_lines) > 5:
        preview_lines += content_lines[:2]
        preview_lines.append("[...]")
        preview_lines += content_lines[-2:]
    else:
        preview_lines = content_lines
    print()
    for l in preview_lines:
        print("    %s" % l)
    print()
    answer = input("looks good? [Y/n] ")
    if answer.lower() == "n":
        print("ok, I will keep it (%s) untouched" % patch_file)
        return

    with open(patch_file, "r") as f:
        cv_orig_content = f.read()
    cv_content = cv_orig_content.replace("*** SUBJECT HERE ***", subject)
    cv_content = cv_content.replace("*** BLURB HERE ***", content)
    with open(patch_file, "w") as f:
        f.write(cv_content)


def fillup_cv_from_commit(patch_file, commit):
    cv_content = (
        subprocess.check_output(["git", "log", "-1", "--pretty=%b", commit])
        .decode()
        .strip()
    )
    # paragraphs
    cv_pars = cv_content.split("\n\n")
    if len(cv_pars) < 2:
        print("Less than two paragraphs.  Forgiving coverletter update.")
        return

    subject = cv_pars[0]
    body_pars = cv_pars[1:]
    for line in body_pars[-1].split("\n"):
        if line.startswith("Signed-off-by:"):
            body_pars = body_pars[:-1]
            break
    content = "\n\n".join(body_pars)

    fillup_cv(patch_file, subject, content)


def find_topic_merge_commit(base_commit, last_commit):
    hashes_lines = (
        subprocess.check_output(["git", "log", "-900", "--pretty=%H %P"])
        .decode()
        .strip()
        .split("\n")
    )
    for hashes in [l.split() for l in hashes_lines]:
        if len(hashes) != 3:
            continue
        if hashes[1] != base_commit or hashes[2] != last_commit:
            continue
        return hashes[0]
    return None


def add_base_or_merge_commit_as_cv(patch_file, base_commit, commit_ids):
    merge_commit = find_topic_merge_commit(base_commit, commit_ids[0])
    if merge_commit is None:
        answer = input("\nMay I add the base commit to the coverletter? [Y/n] ")
        if answer.lower() == "n":
            return

        fillup_cv_from_commit(patch_file, base_commit)
        return

    base_commit_title = (
        subprocess.check_output(["git", "log", "-1", "--pretty=%s", base_commit])
        .decode()
        .strip()
    )
    merge_commit_title = (
        subprocess.check_output(["git", "log", "-1", "--pretty=%s", merge_commit])
        .decode()
        .strip()
    )

    print("\nMay I add below as the coverletter?")
    print()
    print("1. Message of the baseline commit (%s) # default" % base_commit_title)
    print("2. Message of the merge commit (%s)" % merge_commit_title)
    print("3. No, do noting for the coverletter")
    print()
    answer = input("Select: ")
    selections = [base_commit, merge_commit, None]
    try:
        cv_commit = selections[int(answer) - 1]
    except:
        cv_commit = base_commit
    if cv_commit is None:
        return
    fillup_cv_from_commit(patch_file, cv_commit)


def fillup_cv_from_file(patch_file, cv_file):
    with open(cv_file, "r") as f:
        content = f.read()
    pars = content.split("\n\n")
    subject = pars[0]
    content = "\n\n".join(pars[1:])

    print("Adding cover letter content from '%s' as you requested." % cv_file)
    fillup_cv(patch_file, subject, content)


def commit_subject_to_id(subject):
    subjects_txt = subprocess.check_output("git log -2000 --pretty=%s".split()).decode()
    for idx, commit_subject in enumerate(subjects_txt.strip().split("\n")):
        if commit_subject != subject:
            continue
        commit_ids_txt = subprocess.check_output(
            "git log -2000 --pretty=%H".split()
        ).decode()
        return commit_ids_txt.strip().split("\n")[idx]
    return None


def convert_commits_range_txt(txt):
    idx = txt.find("subject(")
    if idx == -1:
        return txt, len(txt)
    if idx != 0:
        return txt[:idx], idx

    subject_chrs = []
    parentheses_to_close = 1
    for idx, c in enumerate(txt[len("subject(") :]):
        if c == "(":
            parentheses_to_close += 1
        elif c == ")":
            parentheses_to_close -= 1
        if parentheses_to_close > 0:
            subject_chrs.append(c)
            continue
        # assume the subject to have balanced parentheses.  If not, this logic
        # fails.
        else:
            break
    processed_len = len("subject(") + idx + 1

    subject = "".join(subject_chrs)
    commit_id = commit_subject_to_id(subject)
    return commit_id, processed_len


def convert_commit_subjects_to_ids(commits_range_txt):
    """
    commits_range_txt is 'git'-supporting commits range specification.  For
    easy specification of commits with frequent rebasing, hkml supports having
    'subject(<subject>)' format in the text, to specify a commit of <subject>
    subject.
    """
    converted_chrs = []
    idx = 0
    while idx < len(commits_range_txt):
        converted_txt, converted_len = convert_commits_range_txt(
            commits_range_txt[idx:]
        )
        converted_chrs.append(converted_txt)
        idx += converted_len
    return "".join(converted_chrs)


def format_patches(args, on_linux_tree):
    commits_range = convert_commit_subjects_to_ids(args.commits)
    commit_ids = [
        hash
        for hash in subprocess.check_output(
            ["git", "log", "--pretty=%H", commits_range]
        )
        .decode()
        .strip()
        .split("\n")
        if hash != ""
    ]
    if len(commit_ids) == 0:
        return None, "no commit to format patch"
    if len(commit_ids) > 1:
        add_cv = True
    else:
        add_cv = False

    base_commit = (
        subprocess.check_output(["git", "rev-parse", "%s^" % commit_ids[-1]])
        .decode()
        .strip()
    )
    cmd = [
        "git",
        "format-patch",
        commits_range,
        "--base",
        base_commit,
        "-o",
        args.output_dir,
    ]
    if add_cv:
        cmd.append("--cover-letter")
    if args.subject_prefix is not None:
        cmd.append("--subject-prefix=%s" % args.subject_prefix)
    elif args.rfc is True:
        cmd.append("--rfc")
    patch_files = subprocess.check_output(cmd).decode().strip().split("\n")
    print("made below patch files")
    print("\n".join(patch_files))
    print()

    err = add_patches_recipients(patch_files, args.to, args.cc, add_cv, on_linux_tree)
    if err is not None:
        return None, "adding recipients fail (%s)" % err

    if add_cv:
        if args.cv is None:
            add_base_or_merge_commit_as_cv(patch_files[0], base_commit, commit_ids)
        else:
            fillup_cv_from_file(patch_files[0], args.cv)
    return patch_files, None


def notify_abort(patch_files):
    print("Aborting remaining works.")
    print(
        " ".join(
            [
                "Patches are generated as below.",
                "You can manually modify those or use 'hkml patch format' again.",
            ]
        )
    )
    print()
    for patch_file in patch_files:
        print("    %s" % patch_file)


def ok_to_continue(patch_files):
    answer = input("Looks good? [Y/n] ")
    if answer.lower() != "n":
        return True
    notify_abort(patch_files)
    return False


def review_patches(on_linux_tree, patch_files):
    """Return whether to abort remaining works"""
    if on_linux_tree and os.path.exists("./scripts/checkpatch.pl"):
        print("\ncheckpatch.pl found.  shall I run it?")
        print("(hint: you can do this manually via 'hkml patch check')")
        answer = input("[Y/n/q] ")
        if answer.lower() == "q":
            return True
        if answer.lower() != "n":
            hkml_patch.check_patches(
                "./scripts/checkpatch.pl", patch_files, None, rm_patches=False
            )
            if not ok_to_continue(patch_files):
                return True

    print("\nwould you review subjects of formatted patches?")
    answer = input("[Y/n/q] ")
    if answer.lower() == "q":
        return True
    if answer.lower() != "n":
        print("below are the subjects")
        for patch_file in patch_files:
            print(_hkml.read_mbox_file(patch_file)[0].subject)
        print()
        if not ok_to_continue(patch_files):
            return True

    print("\nwould you review recipients of formatted patches?")
    print("(hint: you can do this manually via 'hkml patch recipients')")
    answer = input("[Y/n/q] ")
    if answer.lower() == "q":
        return True
    if answer.lower() != "n":
        hkml_patch.list_recipients(patch_files)
    if not ok_to_continue(patch_files):
        return True
    return False


def main(args):
    on_linux_tree = is_linux_tree("./")

    patch_files, err = format_patches(args, on_linux_tree)
    if err is not None:
        print("generating patch files failed (%s)" % err)
        return -1

    abort = review_patches(on_linux_tree, patch_files)
    if abort is True:
        return

    print("\nMay I send the patches?  If you say yes, I will do below")
    print()
    print("    git send-email \\")
    for patch_file in patch_files:
        print("            %s \\" % patch_file)
    print()
    print(
        " ".join(
            [
                "You can manually review and modify the patch files",
                "before answering the next question.",
            ]
        )
    )
    answer = input("Do it? [y/N] ")

    if answer.lower() == "y":
        subprocess.call(["git", "send-email"] + patch_files)


def set_argparser(parser):
    parser.add_argument(
        "commits", metavar="<commits>", help="commits to convert to patch files"
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        metavar="<dir>",
        default="./",
        help="directory to save formatted patch files",
    )
    parser.add_argument("--rfc", action="store_true", help="mark as RFC patches")
    parser.add_argument("--subject_prefix", metavar="<string>", help="subject prefix")
    if sys.version_info >= (3, 7):
        parser.add_argument(
            "--to",
            metavar="<recipient>",
            nargs="+",
            default=[],
            action="extend",
            help="To: recipients",
        )
        parser.add_argument(
            "--cc",
            metavar="<recipient>",
            nargs="+",
            default=[],
            action="extend",
            help="Cc: recipients",
        )
    else:
        parser.add_argument(
            "--to", metavar="<recipient>", nargs="+", default=[], help="To: recipients"
        )
        parser.add_argument(
            "--cc", metavar="<recipient>", nargs="+", default=[], help="Cc: recipients"
        )
    parser.add_argument(
        "--cv", metavar="<file>", help="file containing cover letter content"
    )
    parser.epilog = " ".join(
        [
            "If this is called on linux tree and a source file is given to",
            "--to and/or --cc, get_maintainer.pl found maintainers of the file",
            "are added as To and/or Cc, respectively.",
        ]
    )
