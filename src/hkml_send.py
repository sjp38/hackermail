#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import datetime
import os
import subprocess

import _hkml
import hkml_tag

def draft_or_sent_mail(draft_file, msgid):
    with open(draft_file, 'r') as f:
        draft_content = f.read()
    paragraphs = draft_content.split('\n\n')
    if len(paragraphs) == 0:
        header_lines = []
    else:
        header_lines = paragraphs[0].split('\n')
    has_date = False
    has_msgid = False
    has_from = False
    for line in header_lines:
        if line.startswith('Date: '):
            has_date = True
        if line.startswith('Messagge-ID: '):
            has_msgid = True
        if line.startswith('From: '):
            has_from = True

    fake_header = ['From hkml_draft Thu Jan  1 00:00:00 1970']
    if has_date is False:
        fake_header.append('Date: %s' % datetime.datetime.now().strftime(
            '%a, %d %b %Y %H:%M:%S %z'))
    if has_msgid is False:
        if msgid is None:
            msgid = '%s' % datetime.datetime.now().strftime(
                    'hkml_draft-%Y-%m-%d-%H-%M-%S')
        fake_header.append('Message-ID: %s' % msgid)
    if has_from is False:
        fake_header.append('From: ')
    draft_mbox_str = '\n'.join(fake_header + [draft_content])
    return _hkml.Mail(mbox=draft_mbox_str)

def send_mail(mboxfile, get_confirm, erase_mbox, orig_draft_subject=None):
    do_send = True
    if get_confirm:
        with open(mboxfile, 'r') as f:
            print(f.read())
        print('Above is what you wrote.')
    sent = False
    msgid = None
    for line in _hkml.cmd_lines_output(['git', 'send-email', mboxfile,
                                        # for getting message-id
                                        '--confirm', 'always']):
        fields = line.split()
        if len(fields) == 2 and fields[0].lower() == 'message-id:':
            msgid = fields[1]
        if fields == ['Result:', '250'] or fields == ['Result:' , 'OK']:
            sent = True
    hkml_tag.handle_may_sent_mail(
            draft_or_sent_mail(mboxfile, msgid), sent, orig_draft_subject)
    if erase_mbox:
        os.remove(mboxfile)

def main(args):
    send_mail(args.mbox_file, get_confirm=False, erase_mbox=False)

def set_argparser(parser=None):
    parser.description = 'send a mail'
    parser.add_argument('mbox_file', metavar='<mboxfile>',
            help='Mbox format file of the mail to send.')
