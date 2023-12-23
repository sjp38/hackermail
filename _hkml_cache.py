import json
import os

import _hkml

# dict having gitid/gitdir as key, Mail kvpairs as value
mails_cache = None

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

    key = '%s/%s' % (mail.gitid, mail.gitdir)
    if key in mails_cache:
        return
    mails_cache[key] = mail.to_kvpairs()

def write_mails_cache_file():
    cache_path = os.path.join(_hkml.get_hkml_dir(), 'mails_cache')
    with open(cache_path, 'w') as f:
        json.dump(mails_cache, f, indent=4)
