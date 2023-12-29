import argparse
import datetime
import json
import os

import _hkml

# dict having gitid/gitdir as key, Mail kvpairs as value
mails_cache = None
need_file_update = False

def get_cache_key(gitid, gitdir):
    return '%s/%s' % (gitid, gitdir)

def get_mails_cache():
    global mails_cache

    if mails_cache is not None:
        return mails_cache

    cache_path = os.path.join(_hkml.get_hkml_dir(), 'mails_cache')
    if os.path.isfile(cache_path):
        with open(cache_path, 'r') as f:
            mails_cache = json.load(f)
    else:
        mails_cache = {}
    return mails_cache

def get_mail(gitid, gitdir):
    cache = get_mails_cache()
    key = get_cache_key(gitid, gitdir)
    if not key in cache:
        return None
    return _hkml.Mail.from_kvpairs(cache[key])

def set_mail(mail):
    global need_file_update

    cache = get_mails_cache()
    key = get_cache_key(mail.gitid, mail.gitdir)
    if key in cache:
        return
    cache[key] = mail.to_kvpairs()
    need_file_update = True

def writeback_mails():
    if not need_file_update:
        return
    cache_path = os.path.join(_hkml.get_hkml_dir(), 'mails_cache')
    with open(cache_path, 'w') as f:
        json.dump(get_mails_cache(), f, indent=4)

def evict_mails(date_thres):
    global need_file_update

    date_thres = datetime.datetime.strptime(
            date_thres, '%Y-%m-%d').astimezone()
    cache = get_mails_cache()
    keys_to_del = []
    for key in cache:
        mail = _hkml.Mail.from_kvpairs(cache[key])
        if mail.date < date_thres:
            keys_to_del.append(key)

    for key in keys_to_del:
        need_file_update = True
        del cache[key]

def set_argparser(parser):
    parser.add_argument(
            '--evict_old', metavar='<%Y-%m-%d>',
            help='evict cached mails older than the given date')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.evict_old:
        evict_mails(args.evict_old)
        writeback_mails()
        return

    cache_path = os.path.join(_hkml.get_hkml_dir(), 'mails_cache')
    if not os.path.isfile(cache_path):
        print('no cache exist')
        exit(1)

    cache_stat = os.stat(cache_path)
    print('cache size: %.3f MiB' % (cache_stat.st_size / 1024 / 1024))

    cache = get_mails_cache()
    print('%d mails in cache' % len(mails_cache))

if __name__ == '__main__':
    main()
