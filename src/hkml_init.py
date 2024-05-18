#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import subprocess

def config_sendemail():
    send_configured = subprocess.call(
            ['git', 'config', 'sendemail.smtpserver'],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) == 0
    if send_configured is True:
        return
    question = '  '.join([
        'Seems git send-emtail is not configured.',
        'Please configure it if you want to send email using hkml.',
        'If you use gmail, I can do the configuration instead.',
        'Are you gonna use gmail, and want me to do the configuration? [Y/n] '
        ])
    answer = input(question)
    if answer.lower() == 'n':
        return
    mail_account = input('enter your gmail account (e.g., foo@gmail.com): ')
    cmd = ['git', 'config']
    subprocess.call(cmd + ['sendemail.smtpserver', 'smtp.gmail.com'])
    subprocess.call(cmd + ['sendemail.smtpserverport', '587'])
    subprocess.call(cmd + ['sendemail.smtpencryption', 'tls'])
    subprocess.call(cmd + ['sendemail.smtpuser', mail_account])

def main(args):
    if args.manifest is None:
        print('--manifest is not specified')
        lore_js = os.path.join(
                os.path.dirname(__file__), 'manifests', 'lore.js')
        question = '  '.join([
            '%s is the manifest for lore.kernel.org.' % lore_js,
            'Use it as the manifest? [Y/n] '])
        answer = input(question)
        if answer.lower() == 'n':
            print('Cannot proceed initialization')
            exit(1)
        args.manifest = lore_js
    elif not os.path.isfile(args.manifest):
        print('--manifest (%s) not found' % args.manifest)
        exit(1)

    os.mkdir('.hkm')
    os.mkdir('.hkm/archives')

    with open(args.manifest, 'r') as f:
        content = f.read()
    with open(os.path.join('.hkm', 'manifest'), 'w') as f:
        f.write(content)

    config_sendemail()

def set_argparser(parser=None):
    parser.add_argument('--manifest', metavar='<file>',
            help='manifest file to use')
