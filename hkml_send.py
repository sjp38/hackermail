#!/usr/bin/env python3

import argparse
import os
import subprocess

import _hkml

def set_argparser(parser=None):
    parser.add_argument('mbox_file', metavar='<mboxfile>',
            help='Mbox format file of the mail to send.')

def send_mail(mboxfile, get_confirm=False):
    if get_confirm:
        with open(mboxfile, 'r') as f:
            print(f.read())
        answer = input('Will send above mail.  Okay? [y/N] ')
        if answer.lower() != 'y':
            answer = input('Leave the draft message? [Y/n] ')
            if answer.lower() == 'n':
                os.remove(mboxfile)
            else:
                print('The draft message is at %s' % mboxfile)
            exit(0)
    _hkml.cmd_str_output(['git', 'send-email', mboxfile])

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    send_mail(args.mbox_file, get_confirm=False)

if __name__ == '__main__':
    main()
