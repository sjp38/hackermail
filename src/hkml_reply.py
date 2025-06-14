# SPDX-License-Identifier: GPL-2.0

import tempfile

import _hkml
import _hkml_list_cache
import hkml_send
import hkml_write


def format_reply_subject(mail):
    subject = mail.get_field("subject")
    if subject and subject.split()[0].lower() != "re:":
        subject = "Re: %s" % subject
    return subject


def format_reply(mail, attach_file):
    subject = format_reply_subject(mail)
    in_reply_to = mail.get_field("message-id")
    cc = [x for x in [mail.get_field("to"), mail.get_field("cc")] if x]
    to = [mail.get_field("from")]

    body_lines = []
    date = mail.get_field("date")
    if date and to[0]:
        body_lines.append("On %s %s wrote:" % (date, to[0]))
        body_lines.append("")
    body = mail.get_field("body")
    for line in body.split("\n"):
        body_lines.append("> %s" % line)
    body = "\n".join(body_lines)
    return hkml_write.format_mbox(
        subject,
        in_reply_to,
        to,
        cc,
        body,
        from_=None,
        draft_mail=None,
        attach_files=attach_file,
    )


def reply(mail, attach_files, format_only):
    reply_mbox_str = format_reply(mail, attach_files)
    if format_only:
        print(reply_mbox_str)
        return

    fd, reply_tmp_path = tempfile.mkstemp(prefix="hkml_reply_")
    with open(reply_tmp_path, "w") as f:
        f.write(reply_mbox_str)
    err = hkml_write.open_editor(reply_tmp_path)
    if err is not None:
        print(err)
        exit(1)
    hkml_send.send_mail(
        reply_tmp_path, get_confirm=True, erase_mbox=True, orig_draft_subject=None
    )


def main(args):
    if args.mail.isdigit():
        mail = _hkml_list_cache.get_mail(int(args.mail))
    elif args.mail == "clipboard":
        mails, err = _hkml.read_mails_from_clipboard()
        if err != None:
            print("reading mails in clipboard failed: %s" % err)
            exit(1)
        if len(mails) != 1:
            print("multiple mails in clipboard")
            exit(1)
        mail = mails[0]
    else:
        print("unsupported <mail> (%s)" % args.mail)

    if mail is None:
        print("mail is not cached")
        exit(1)

    reply(mail, args.attach, args.format_only)


def set_argparser(parser):
    parser.description = "reply to a mail"
    parser.add_argument(
        "mail",
        metavar="<mail>",
        help=" ".join(
            ["The mail to reply to.", "Could be index on the list, or 'clipboard'"]
        ),
    )
    hkml_write.add_common_arguments(parser)
