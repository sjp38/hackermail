#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import subprocess

import hkml_manifest


def config_sendemail():
    send_configured = (
        subprocess.call(
            ["git", "config", "sendemail.smtpserver"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        == 0
    )
    if send_configured is True:
        return
    question = "  ".join(
        [
            "Seems git send-email is not configured.",
            "Please configure it if you want to send email using hkml.",
            "If you use gmail, I can do the configuration instead.",
            "Are you gonna use gmail, and want me to do the configuration? [Y/n] ",
        ]
    )
    answer = input(question)
    if answer.lower() == "n":
        return
    mail_account = input("enter your gmail account (e.g., foo@gmail.com): ")
    cmd = ["git", "config"]
    subprocess.call(cmd + ["sendemail.smtpserver", "smtp.gmail.com"])
    subprocess.call(cmd + ["sendemail.smtpserverport", "587"])
    subprocess.call(cmd + ["sendemail.smtpencryption", "tls"])
    subprocess.call(cmd + ["sendemail.smtpuser", mail_account])


def main(args):
    os.mkdir(".hkm")
    os.mkdir(".hkm/archives")

    if args.manifest is None:
        question = " ".join(
            [
                "--manifest is not specified.",
                "May I set it up for lore.kernel.org? [Y/n] ",
            ]
        )
        answer = input(question)
        if answer.lower() == "n":
            print("Cannot proceed initialization")
            os.rmdir(".hkm/archives")
            os.rmdir(".hkm")
            exit(1)
        err = hkml_manifest.fetch_lore()
        if err:
            print("Fetching lore manifest failed (err).")
            print("Please check if you have internet access to kernel.org.")
            os.rmdir(".hkm/archives")
            os.rmdir(".hkm")
            exit(1)
    else:
        if not os.path.isfile(args.manifest):
            print("--manifest (%s) not found" % args.manifest)
            exit(1)

        with open(args.manifest, "r") as f:
            content = f.read()
        with open(os.path.join(".hkm", "manifest"), "w") as f:
            f.write(content)

    config_sendemail()


def set_argparser(parser=None):
    parser.add_argument("--manifest", metavar="<file>", help="manifest file to use")
