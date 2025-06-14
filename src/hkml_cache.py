# SPDX-License-Identifier: GPL-2.0

import argparse
import datetime
import json
import os
import sys
import time

import _hkml

# Cache is constructed with multiple files.
# active cache: Contains most recently added cache entries.
# archieved cache: Contains cache entries that added older than oldest one in
# the active cache.
#
# Size of cache files are limited to about 100 MiB by default.
# Up to 9 archived cache files can exist by default.
# When the size of active cache becomes >=100 MiB, delete oldest archived
# cache, make the active cache a newest archived cache, and create a new active
# cache.
#
# When reading the cache, active cache is first read, then archived caches one
# by one, recent archive first, until the item is found.


def load_cache_config():
    cache_config_path = os.path.join(_hkml.get_hkml_dir(), "mails_cache_config")
    if not os.path.isfile(cache_config_path):
        return {"max_active_cache_sz": 100 * 1024 * 1024, "max_archived_caches": 9}

    with open(cache_config_path, "r") as f:
        return json.load(f)


def set_cache_config(max_active_cache_sz, max_archived_caches):
    cache_config_path = os.path.join(_hkml.get_hkml_dir(), "mails_cache_config")
    with open(cache_config_path, "w") as f:
        json.dump(
            {
                "max_active_cache_sz": max_active_cache_sz,
                "max_archived_caches": max_archived_caches,
            },
            f,
            indent=4,
        )


# dict having gitid/gitdir as key, Mail kvpairs as value

archived_caches = []
active_cache = None

need_file_update = False


def get_cache_key(gitid=None, gitdir=None, msgid=None):
    if gitid is not None:
        return "%s/%s" % (gitid, gitdir)
    return msgid


def list_archive_files():
    """Return a list of archived cache files sorted in recent one first"""
    archive_files = []
    for file_ in os.listdir(_hkml.get_hkml_dir()):
        if file_.startswith("mails_cache_archive_"):
            archive_files.append(os.path.join(_hkml.get_hkml_dir(), file_))
    # name is mails_cache_archive_<timestamp>
    archive_files.sort(reverse=True)
    return archive_files


def get_active_mails_cache():
    global active_cache

    if active_cache is not None:
        return active_cache

    active_cache = {}
    cache_path = os.path.join(_hkml.get_hkml_dir(), "mails_cache_active")
    if os.path.isfile(cache_path):
        stat = os.stat(cache_path)
        if stat.st_size >= load_cache_config()["max_active_cache_sz"]:
            os.rename(
                cache_path,
                os.path.join(
                    _hkml.get_hkml_dir(),
                    "mails_cache_archive_%s"
                    % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                ),
            )
            archive_files = list_archive_files()
            if len(archive_files) > load_cache_config()["max_archived_caches"]:
                os.remove(archive_files[-1])
        else:
            with open(cache_path, "r") as f:
                active_cache = json.load(f)
    return active_cache


def load_one_more_archived_cache():
    global archived_caches

    archive_files = list_archive_files()
    if len(archive_files) == len(archived_caches):
        return False
    with open(archive_files[len(archived_caches)], "r") as f:
        archived_caches.append(json.load(f))
    return True


def __get_kvpairs(key, cache):
    if not key in cache:
        # msgid_key_map has introduced from v1.1.6
        if "msgid_key_map" in cache and key in cache["msgid_key_map"]:
            key = cache["msgid_key_map"][key]
    if not key in cache:
        return None
    return cache[key]


def get_kvpairs(gitid=None, gitdir=None, key=None):
    global archived_caches

    if key is None:
        key = get_cache_key(gitid, gitdir)

    cache = get_active_mails_cache()
    kvpairs = __get_kvpairs(key, cache)
    if kvpairs is not None:
        return kvpairs

    for cache in archived_caches:
        kvpairs = __get_kvpairs(key, cache)
        if kvpairs is not None:
            return kvpairs

    while load_one_more_archived_cache() == True:
        kvpairs = __get_kvpairs(key, archived_caches[-1])
        if kvpairs is not None:
            return kvpairs

    return None


def get_mail(gitid=None, gitdir=None, key=None):
    kvpairs = get_kvpairs(gitid, gitdir, key)
    if kvpairs is not None:
        return _hkml.Mail(kvpairs=kvpairs)
    return None


def get_mbox(gitid=None, gitdir=None, key=None):
    kvpairs = get_kvpairs(gitid, gitdir, key)
    if "mbox" in kvpairs:
        return kvpairs["mbox"]
    return None


def skip_overwrite(mail, cache, key):
    if not key in cache:
        return True
    cached_kvpair = cache[key]
    mail_kvpair = mail.to_kvpairs()
    for mkey in mail_kvpair.keys():
        if not mkey in cached_kvpair:
            return False
        if mail_kvpair[mkey] != cached_kvpair[mkey]:
            return False
    return True


def set_mail(mail, overwrite=False):
    global need_file_update

    if mail.broken():
        return

    cache = get_active_mails_cache()
    msgid = mail.get_field("message-id")
    if mail.gitid is not None and mail.gitdir is not None:
        key = get_cache_key(mail.gitid, mail.gitdir)
        # msgid_key_map has introduced from v1.1.6
        if not "msgid_key_map" in cache:
            cache["msgid_key_map"] = {}
        cache["msgid_key_map"][msgid] = key
    else:
        key = msgid
    if overwrite is False:
        if key in cache:
            return
        for archived_cache in archived_caches:
            if key in archived_cache:
                return
    else:
        if skip_overwrite(mail, cache, key):
            return

    cache[key] = mail.to_kvpairs()
    need_file_update = True


def writeback_mails():
    if not need_file_update:
        return
    cache_path = os.path.join(_hkml.get_hkml_dir(), "mails_cache_active")
    with open(cache_path, "w") as f:
        json.dump(get_active_mails_cache(), f, indent=4)


def pr_cache_stat(cache_path, profile_mail_parsing_time):
    print("Stat of %s" % cache_path)
    cache_stat = os.stat(cache_path)
    print("cache size: %.3f MiB" % (cache_stat.st_size / 1024 / 1024))

    before_timestamp = time.time()
    with open(cache_path, "r") as f:
        cache = json.load(f)
    print("%d mails in cache" % len(cache))
    print("%f seconds for json-loading cache" % (time.time() - before_timestamp))

    if profile_mail_parsing_time is not True:
        return
    before_timestamp = time.time()
    for key in cache:
        mail = _hkml.Mail(kvpairs=cache[key])
    print("%f seconds for parsing mails" % (time.time() - before_timestamp))


def show_cache_status(config_only, profile_mail_parsing_time):
    cache_config = load_cache_config()
    print("max active cache file size: %s bytes" % cache_config["max_active_cache_sz"])
    print("max archived caches: %d" % cache_config["max_archived_caches"])
    if config_only is True:
        return
    print()

    cache_path = os.path.join(_hkml.get_hkml_dir(), "mails_cache_active")
    if not os.path.isfile(cache_path):
        print("no cache exist")
        exit(1)

    pr_cache_stat(cache_path, profile_mail_parsing_time)
    print("")
    for archived_cache in list_archive_files():
        pr_cache_stat(archived_cache, profile_mail_parsing_time)
        print("")


def main(args):
    if args.action == "status":
        show_cache_status(args.config_only, args.profile_mail_parsing_time)
    elif args.action == "config":
        set_cache_config(args.max_active_cache_sz, args.max_archived_caches)


def set_argparser(parser):
    parser.description = "manage mails cache"

    if sys.version_info >= (3, 7):
        subparsers = parser.add_subparsers(
            title="action", dest="action", metavar="<action>", required=True
        )
    else:
        subparsers = parser.add_subparsers(
            title="action", dest="action", metavar="<action>"
        )

    parser_status = subparsers.add_parser("status", help="show cache status")
    parser_status.add_argument(
        "--config_only", action="store_true", help="show configuration status only"
    )
    parser_status.add_argument(
        "--profile_mail_parsing_time",
        action="store_true",
        help="measure and show mails parsing time",
    )

    parser_config = subparsers.add_parser("config", help="setup cache configuration")
    parser_config.add_argument(
        "max_active_cache_sz",
        type=int,
        metavar="<bytes>",
        help="maximum size of active cache",
    )
    parser_config.add_argument(
        "max_archived_caches",
        type=int,
        metavar="<int>",
        help="maximum number of archived caches",
    )
