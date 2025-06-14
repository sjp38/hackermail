# SPDX-License-Identifier: GPL-2.0

import tempfile

import _hkml
import _hkml_list_cache
import hkml_open
import hkml_send
import hkml_write


def forward(
    mail,
    subject=None,
    in_reply_to=None,
    to=None,
    cc=None,
    attach_files=None,
    format_only=None,
):
    mail_str = "\n".join(["=== >8 ===", hkml_open.mail_display_str(mail)])

    if subject is None:
        subject = "Fwd: %s" % mail.subject

    mbox = hkml_write.format_mbox(
        subject,
        in_reply_to,
        to,
        cc,
        mail_str,
        from_=None,
        draft_mail=None,
        attach_files=attach_files,
    )

    if format_only:
        print(mbox)
        return

    fd, tmp_path = tempfile.mkstemp(prefix="hkml_forward_")
    with open(tmp_path, "w") as f:
        f.write(mbox)
    err = hkml_write.open_editor(tmp_path)
    if err is not None:
        print(err)
        exit(1)
    hkml_send.send_mail(
        tmp_path, get_confirm=True, erase_mbox=True, orig_draft_subject=None
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

    forward(
        mail,
        args.subject,
        args.in_reply_to,
        args.to,
        args.cc,
        args.attach,
        args.format_only,
    )


def set_argparser(parser):
    parser.description = "forward a mail"
    parser.add_argument(
        "mail",
        metavar="<mail>",
        help=" ".join(
            ["The mail to forward.", "Could be index on the list, or 'clipboard'"]
        ),
    )
    parser.add_argument(
        "--subject", metavar="<subject>", type=str, help="Subject of the mail."
    )
    parser.add_argument(
        "--in-reply-to",
        metavar="<message id>",
        help="Add in-reply-to field in the mail header",
    )
    parser.add_argument(
        "--to", metavar="<email address>", nargs="+", help="recipients of the mail"
    )
    parser.add_argument(
        "--cc", metavar="<email address>", nargs="+", help="cc recipients of the mail"
    )
    hkml_write.add_common_arguments(parser)
