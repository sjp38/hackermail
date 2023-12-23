import argparse
import json
import os

import _hkml

# dict having gitid/gitdir as key, Mail kvpairs as value
mails_cache = None
need_file_update = False

def read_mail_from_cache(gitid, gitdir):
    global mails_cache

    if mails_cache is None:
        cache_path = os.path.join(_hkml.get_hkml_dir(), 'mails_cache')
        if not os.path.isfile(cache_path):
            mails_cache = {}
        else:
            with open(cache_path, 'r') as f:
                mails_cache = json.load(f)

    key = '%s/%s' % (gitid, gitdir)
    if not key in mails_cache:
        return None
    return _hkml.Mail.from_kvpairs(mails_cache['%s/%s' % (gitid, gitdir)])

def write_mail_to_cache(mail):
    global mails_cache
    global need_file_update

    key = '%s/%s' % (mail.gitid, mail.gitdir)
    if key in mails_cache:
        return
    mails_cache[key] = mail.to_kvpairs()
    need_file_update = True

def write_mails_cache_file():
    if not need_file_update:
        return
    cache_path = os.path.join(_hkml.get_hkml_dir(), 'mails_cache')
    with open(cache_path, 'w') as f:
        json.dump(mails_cache, f, indent=4)

def set_argparser(parser):
    return

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    cache_path = os.path.join(_hkml.get_hkml_dir(), 'mails_cache')
    if not os.path.isfile(cache_path):
        print('no cache exist')
        exit(1)

    cache_stat = os.stat(cache_path)
    print('cache size: %.3f MiB' % (cache_stat.st_size / 1024 / 1024))

    with open(cache_path, 'r') as f:
        mails_cache = json.load(f)
    print('%d mails in cache' % len(mails_cache))

if __name__ == '__main__':
    main()
