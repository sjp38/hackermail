# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile

import _hkml
import _hkml_list_cache
import hkml_common
import hkml_list
import hkml_view


def decorate_last_reference(text):
    lines = text.split("\n")
    if not lines[0].startswith("# last reference: "):
        return text

    fields = lines[0].split()
    if len(fields) != 4:
        return text
    last_reference_idx = int(lines[0].split()[3])
    for idx, line in enumerate(lines):
        fields = line.split()
        if len(fields) == 0:
            continue
        if not fields[0].startswith("[") or not fields[0].endswith("]"):
            continue
        try:
            mail_idx = int(fields[0][1:-1])
        except:
            continue
        if mail_idx != last_reference_idx:
            continue
        line = "\u001b[32m" + line + "\u001b[0m"
        line = "\x1b[3m" + line + "\x1b[0m"
        del lines[idx]
        lines.insert(idx, line)
        text = "\n".join(lines)
    return text


def pr_with_pager_if_needed(text):
    text = decorate_last_reference(text)

    try:
        if text.count("\n") < (os.get_terminal_size().lines * 9 / 10):
            print(text)
            return
    except OSError as e:
        # maybe the user is using pipe to the output
        pass

    fd, tmp_path = tempfile.mkstemp(prefix="hkml_open-")
    with open(tmp_path, "w") as f:
        f.write(text)
    subprocess.call(["less", "-R", "-M", "--no-init", tmp_path])
    os.remove(tmp_path)


def mail_display_str(
    mail,
    head_columns=None,
    valid_mbox=False,
    for_draft_continue=False,
    recipients_per_line=False,
):
    lines = []
    if valid_mbox is True:
        lines.append("From hackermail Thu Jan  1 00:00:00 1970")
    if for_draft_continue is True:
        head_fields = ["From", "To", "Cc", "In-Reply-To"]
    else:
        head_fields = ["From", "To", "Cc", "Message-Id", "In-Reply-To", "Date"]
    if valid_mbox is False and for_draft_continue is False:
        head_fields.append("Local-Date")
    head_fields.append("Subject")
    for head in head_fields:
        value = mail.get_field(head)
        if value:
            if head in ["To", "Cc"] and recipients_per_line is True:
                recipients = value.split(",")
                for recipient in recipients:
                    lines.append("%s: %s" % (head, recipient.strip()))
                continue
            if head_columns is not None:
                lines += hkml_list.wrap_line("%s:" % head, value, head_columns)
            else:
                lines.append("%s: %s" % (head, value))
    lines.append("\n%s" % mail.get_field("body"))
    return "\n".join(lines)


def last_open_mail_idx():
    with open(os.path.join(_hkml.get_hkml_dir(), "last_open_idx"), "r") as f:
        return int(f.read())


def show_text(text, to_stdout, use_less, string_after_less, data=None):
    if to_stdout:
        print(text)
        return
    if use_less:
        pr_with_pager_if_needed(text)
        if string_after_less is not None:
            print(string_after_less)
    else:
        if type(data) == _hkml.Mail:
            hkml_view.view_mail(text, data)
        else:
            hkml_view.view_text(text)


def show_git_commit(commit, to_stdout, use_less, string_after_less):
    try:
        show_text(
            subprocess.check_output(["git", "show", commit]).decode(),
            to_stdout,
            use_less,
            string_after_less,
            data=None,
        )
        return None
    except:
        return "git show failed"


def handle_command_target(args):
    print("...")
    cmd = args.target.split()[0]
    is_cmd = hkml_common.cmd_available(cmd)
    if not is_cmd:
        return False

    try:
        output = subprocess.check_output(args.target, shell=True).decode()
    except:
        print("failed running the target command")
        return False
    show_text(output, args.stdout, args.use_less, None, data=None)
    return True


def main(args):
    if handle_command_target(args):
        return
    if os.path.isfile(args.target):
        with open(args.target, "r") as f:
            return show_text(f.read(), args.stdout, args.use_less, None, data=None)
    if not args.target.isdigit():
        return show_git_commit(args.target, args.stdout, args.use_less, None)

    noti_current_index = True
    if args.target == "prev":
        args.target = last_open_mail_idx() - 1
    elif args.target == "next":
        args.target = last_open_mail_idx() + 1
    else:
        noti_current_index = False
        args.target = int(args.target)

    mail = _hkml_list_cache.get_mail(args.target)
    if mail is None:
        print("mail is not cached.  Try older list")
        mail = _hkml_list_cache.get_mail(args.target, not_thread_idx=True)
        if mail is None:
            print("even not an older list index.  Maybe git commit?")
            error = show_git_commit(
                "%s" % args.target, args.stdout, args.use_less, None
            )
            if error is not None:
                print("cannot handle the request: %s" % error)
                exit(1)

    with open(os.path.join(_hkml.get_hkml_dir(), "last_open_idx"), "w") as f:
        f.write("%d" % args.target)

    try:
        head_columns = int(os.get_terminal_size().columns * 9 / 10)
    except:
        # maybe user is pipe-ing the output
        head_columns = None
    mail_str = mail_display_str(mail, head_columns)

    string_after_less = None
    if args.use_less and noti_current_index:
        string_after_less = "# you were reading %d-th index" % args.target
    show_text(mail_str, args.stdout, args.use_less, string_after_less, data=mail)


def set_argparser(parser):
    parser.description = "open a mail"
    parser.add_argument(
        "target",
        metavar="<target>",
        help=" ".join(
            [
                "Target to open. Following types are supported.",
                "1. Index of a mail from the last open mails list/thread.",
                "2. 'next': last open mail index plus one.",
                "3. 'prev': last open mail index minus one.",
                "4. text file",
                "5. Git commit",
                "6. command.",
            ]
        ),
    )
    parser.add_argument("--stdout", action="store_true", help="print without a pager")
    parser.add_argument(
        "--use_less", action="store_true", help="use less instead of hkml viewer"
    )
