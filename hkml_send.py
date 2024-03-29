#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import datetime
import os
import subprocess

import _hkml
import hkml_tag

def tag_as_draft(draft_file):
    with open(draft_file, 'r') as f:
        draft_content = f.read()
    fake_mbox_header = 'From hkml_draft Thu Jan  1 00:00:00 1970'
    fake_date = 'Date: %s' % datetime.datetime.now().strftime(
            '%a, %d %b %Y %H:%M:%S %z')
    fake_msgid = 'Message-ID: %s' % datetime.datetime.now().strftime(
            'hkml_draft-%Y-%m-%d-%H-%M-%S')
    draft_mbox_str = '\n'.join(
            [fake_mbox_header, fake_date, fake_msgid, draft_content])
    draft_mail = _hkml.Mail(mbox=draft_mbox_str)
    hkml_tag.do_add_tags(draft_mail, ['drafts'])

def set_argparser(parser=None):
    parser.description = 'send a mail'
    parser.add_argument('mbox_file', metavar='<mboxfile>',
            help='Mbox format file of the mail to send.')

def send_mail(mboxfile, get_confirm=False):
    if get_confirm:
        with open(mboxfile, 'r') as f:
            print(f.read())
        answer = input('Will send above mail.  Okay? [y/N] ')
        if answer.lower() != 'y':
            answer = input('Tag as drafts? [Y/n] ')
            if answer.lower() != 'n':
                tag_as_draft(mboxfile)
            answer = input('Add to the drafts list? [Y/n] ')
            if answer.lower() != 'n':
                hkml_drafts.add_draft(mboxfile)
            answer = input('Leave the draft message? [Y/n] ')
            if answer.lower() == 'n':
                os.remove(mboxfile)
            else:
                print('The draft message is at %s' % mboxfile)
            return
    _hkml.cmd_str_output(['git', 'send-email', mboxfile])
    os.remove(mboxfile)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    send_mail(args.mbox_file, get_confirm=False)

if __name__ == '__main__':
    main()
