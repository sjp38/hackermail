# SPDX-License-Identifier: GPL-2.0

import json
import os
import subprocess
import tempfile

import _hkml
import hkml_cache
import hkml_list

def pr_with_pager_if_needed(text):
    try:
        if text.count('\n') < os.get_terminal_size().lines:
            print(text)
            return
    except OSError as e:
        # maybe the user is using pipe to the output
        pass

    fd, tmp_path = tempfile.mkstemp(prefix='hkml_open-')
    with open(tmp_path, 'w') as f:
        f.write(text)
    subprocess.call(['less', '-M', '--no-init', tmp_path])
    os.remove(tmp_path)

def mail_display_str_via_lore(mail_url):
    lines = []
    try:
        from_lore = _hkml.cmd_lines_output(['w3m', '-dump', mail_url])[3:]
    except:
        sys.stderr.write('\'w3m\' invocation failed.\n')
        exit(1)
    divide_line = '━' * 79
    for line in from_lore:
        if line.strip() == divide_line:
            break
        lines.append(line)
    return '\n'.join(lines)

def mail_display_str(mail, use_lore, show_lore_link):
    if use_lore:
        return mail_display_str_via_lore(lore_url(mail))

    lines = ['Local-Date: %s' % mail.date]
    for head in ['Date', 'Subject', 'Message-Id', 'From', 'To', 'CC']:
        value = mail.get_field(head)
        if value:
            lines.append('%s: %s' % (head, value))
    lines.append('\n%s' % mail.get_field('body'))
    if show_lore_link:
        lines.append('\n%s\n' % lore_url(mail))
    return '\n'.join(lines)

def set_argparser(parser):
    parser.add_argument(
            'mail_idx', metavar='<index>', type=int,
            help='index of the mail to open and read')
    parser.add_argument(
            '--stdout', action='store_true', help='print without a pager')

def main(args=None):
    if not args:
        parser = argparser.ArgumentParser()
        set_Argparser(parser)
        args = parser.parse_args()

    key = hkml_list.get_mail_cache_key(args.mail_idx)
    mail = hkml_cache.get_mail(key=key)
    if mail is None:
        print('mail is not cached')
        exit(1)

    with open(os.path.join(_hkml.get_hkml_dir(), 'last_open_idx'), 'w') as f:
        f.write(args.mail_idx)

    mail_str = mail_display_str(mail, False, False)

    if args.stdout:
        print(mail_str)
        return
    pr_with_pager_if_needed(mail_str)

if __name__ == 'main__':
    main()
