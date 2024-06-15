# SPDX-License-Identifier: GPL-2.0

import json
import os
import subprocess
import tempfile

import _hkml
import hkml_list
import hkml_view

def decorate_last_reference(text):
    lines = text.split('\n')
    if not lines[0].startswith('# last reference: '):
        return text

    fields = lines[0].split()
    if len(fields) != 4:
        return text
    last_reference_idx = int(lines[0].split()[3])
    for idx, line in enumerate(lines):
        fields = line.split()
        if len(fields) == 0:
            continue
        if not fields[0].startswith('[') or not fields[0].endswith(']'):
            continue
        try:
            mail_idx = int(fields[0][1:-1])
        except:
            continue
        if mail_idx != last_reference_idx:
            continue
        line = u'\u001b[32m' + line + u'\u001b[0m'
        line = '\x1B[3m' + line + '\x1B[0m'
        del lines[idx]
        lines.insert(idx, line)
        text = '\n'.join(lines)
    return text

def pr_with_pager_if_needed(text):
    text = decorate_last_reference(text)

    try:
        if text.count('\n') < (os.get_terminal_size().lines * 9 / 10):
            print(text)
            return
    except OSError as e:
        # maybe the user is using pipe to the output
        pass

    fd, tmp_path = tempfile.mkstemp(prefix='hkml_open-')
    with open(tmp_path, 'w') as f:
        f.write(text)
    subprocess.call(['less', '-R', '-M', '--no-init', tmp_path])
    os.remove(tmp_path)

def mail_display_str(mail, head_columns=None):
    lines = []
    for head in ['From', 'To', 'CC', 'Subject', 'Message-Id', 'Date']:
        value = mail.get_field(head)
        if value:
            if head_columns is not None:
                lines += hkml_list.wrap_line('%s:' % head, value, head_columns)
            else:
                lines.append('%s: %s' % (head, value))
    lines.append('Local-Date: %s' % mail.date)
    lines.append('\n%s' % mail.get_field('body'))
    return '\n'.join(lines)

def last_open_mail_idx():
    with open(os.path.join(_hkml.get_hkml_dir(), 'last_open_idx'), 'r') as f:
        return int(f.read())

def main(args):
    noti_current_index = True
    if args.target == 'prev':
        args.target = last_open_mail_idx() - 1
    elif args.target == 'next':
        args.target = last_open_mail_idx() + 1
    else:
        noti_current_index = False
        args.target = int(args.target)

    mail = hkml_list.get_mail(args.target)
    if mail is None:
        print('mail is not cached.  Try older list')
        mail = hkml_list.get_mail(args.target, not_thread_idx=True)
        if mail is None:
            print('even not an older list index.  Forgiving.')
            exit(1)

    with open(os.path.join(_hkml.get_hkml_dir(), 'last_open_idx'), 'w') as f:
        f.write('%d' % args.target)

    try:
        head_columns = int(os.get_terminal_size().columns * 9 / 10)
    except:
        # maybe user is pipe-ing the output
        head_columns = None
    mail_str = mail_display_str(mail, head_columns)

    if args.stdout:
        print(mail_str)
        return
    if args.use_less:
        pr_with_pager_if_needed(mail_str)
        if noti_current_index is True:
            print('# you were reading %d-th index' % args.target)
    else:
        hkml_view.view(mail_str, None)

def set_argparser(parser):
    parser.description = 'open a mail'
    parser.add_argument(
            'target', metavar='<target>',
            help=' '.join(
                [
                    'Target to open. Following types are supported.',
                    '1. Index of a mail from the last open mails list/thread.',
                    '2. \'next\': last open mail index plus one.',
                    '3. \'prev\': last open mail index minus one.',
                    ]))
    parser.add_argument(
            '--stdout', action='store_true', help='print without a pager')
    parser.add_argument(
            '--use_less', action='store_true',
            help='use less instead of hkml viewer')
