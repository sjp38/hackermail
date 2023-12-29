import json
import os
import subprocess
import tempfile

import _hkml
import hkml_cache
import hkml_list

def pr_with_pager_if_needed(lines):
    try:
        if len(lines) < os.get_terminal_size().lines:
            print('\n'.join(lines))
            return
    except OSError as e:
        # maybe the user is using pipe to the output
        pass

    fd, tmp_path = tempfile.mkstemp(prefix='hkml_open-')
    with open(tmp_path, 'w') as f:
        f.write('\n'.join(lines))
    subprocess.call(['less', '--no-init', tmp_path])
    os.remove(tmp_path)

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

    with open(os.path.join(_hkml.get_hkml_dir(), 'mail_idx_to_cache_key'),
              'r') as f:
        key = json.load(f)['%d' % args.mail_idx]
    mail = hkml_cache.get_mail(key=key)
    if mail is None:
        print('mail is not cached')
        exit(1)

    lines = []
    hkml_list.pr_mail_content(mail, False, False, lines)

    if args.stdout:
        print('\n'.join(lines))
        return
    pr_with_pager_if_needed(lines)

if __name__ == 'main__':
    main()
