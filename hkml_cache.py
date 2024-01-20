# SPDX-License-Identifier: GPL-2.0

import argparse
import datetime
import json
import os
import time

import _hkml

# Cache is constructed with multiple files.
# last cache: Contains most recently added cache entries.
# archieved cache: Contains cache entries that added older than oldest one in
# last cache.
#
# Size of cache files are limited to about 100 MiB.
# Up to 9 archived cache files can exist.
# When the size of last cache becomes >=100 MiB, delete oldest archived cache,
# make the last cache a newest archived cache, and create a new last cache. 
#
# When reading the cache, last cache is first read, then archived caches one by
# one, recent archive first, until the item is found.

# dict having gitid/gitdir as key, Mail kvpairs as value
max_archived_caches = 9
archived_caches = []
last_cache = None
total_cache = {}

mails_cache = None
need_file_update = False

def get_cache_key(gitid=None, gitdir=None, msgid=None):
    if gitid is not None:
        return '%s/%s' % (gitid, gitdir)
    return msgid

def list_archive_files():
    """Return a list of archived cache files sorted in recent one first"""
    archive_files = []
    for file_ in os.listdir(_hkml.get_hkml_dir()):
        if file_.startswith('mails_cache_archive_'):
            archive_files.append(
                    os.path.join(_hkml.get_hkml_dir(), file_))
    # name is mails_cache_archive_<timestamp>
    archive_files.sort(reverse=True)
    return archive_files

def get_last_mails_cache():
    global last_cache

    if last_cache is not None:
        return last_cache

    cache_path = os.path.join(_hkml.get_hkml_dir(), 'mails_cache_last')
    if os.path.isfile(cache_path):
        stat = os.stat(cache_path)
        if stat.st_size >= 100 * 1024 * 1024:
            os.rename(
                    cache_path, os.path.join(
                        _hkml.get_hkml_dir(), 'mails_cache_archive_%s' %
                        datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')))
            archive_files = list_archive_files()
            if len(archive_files) > max_archived_caches:
                os.remove(archive_files[-1])
            last_cache = {}
        else:
            with open(cache_path, 'r') as f:
                last_cache = json.load(f)
    return last_cache

def load_one_more_archived_cache():
    global archived_caches

    archive_files = list_archive_files()
    if len(archive_files) == len(archived_caches):
        return False
    with open(archive_files[len(archived_caches)], 'r') as f:
        archived_caches.append(json.load(f))
    return True

def get_mail(gitid=None, gitdir=None, key=None):
    global archived_caches

    if key is None:
        key = get_cache_key(gitid, gitdir)

    cache = get_last_mails_cache()
    if key in cache:
        return _hkml.Mail(kvpairs=cache[key])
    for cache in archived_caches:
        if key in cache:
            return _hkml.Mail(kvpairs=cache[key])
    while load_one_more_archived_cache() == True:
        if key in archived_caches[-1]:
            return _hkml.Mail(kvpairs=archived_caches[-1][key])
    return None

def set_mail(mail):
    global need_file_update

    if mail.broken():
        return

    cache = get_last_mails_cache()
    if mail.gitid is not None and mail.gitdir is not None:
        key = get_cache_key(mail.gitid, mail.gitdir)
    else:
        key = mail.get_field('message-id')
    if key in cache:
        return
    for archived_cache in archived_caches:
        if key in archived_cache:
            return
    cache[key] = mail.to_kvpairs()
    need_file_update = True

def writeback_mails():
    if not need_file_update:
        return
    cache_path = os.path.join(_hkml.get_hkml_dir(), 'mails_cache_last')
    with open(cache_path, 'w') as f:
        json.dump(get_last_mails_cache(), f, indent=4)

def evict_mails(date_thres):
    global need_file_update

    date_thres = datetime.datetime.strptime(
            date_thres, '%Y-%m-%d').astimezone()
    cache = get_last_mails_cache()
    keys_to_del = []
    for key in cache:
        mail = _hkml.Mail(kvpairs=cache[key])
        if mail.date < date_thres:
            keys_to_del.append(key)

    for key in keys_to_del:
        need_file_update = True
        del cache[key]

def pr_cache_stat(cache_path):
    cache_stat = os.stat(cache_path)
    print('cache size: %.3f MiB' % (cache_stat.st_size / 1024 / 1024))

    before_timestamp = time.time()
    cache = get_last_mails_cache()
    print('%d mails in cache' % len(cache))
    print('%f seconds for loading cache' % (time.time() - before_timestamp))

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

    cache_path = os.path.join(_hkml.get_hkml_dir(), 'mails_cache_last')
    if not os.path.isfile(cache_path):
        print('no cache exist')
        exit(1)

    pr_cache_stat(cache_path)

if __name__ == '__main__':
    main()
