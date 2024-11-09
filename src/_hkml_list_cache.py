#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import datetime
import os
import json

import _hkml
import hkml_cache

'''
Contains list command generated outputs to cache for later fast processing.
Keys are the json string of the list command arguments, or 'thread_output'.
Values are a dict containing below key/values.
- 'output': the list command's terminal output string.
- 'index_to_cache_key': a dict having the mail index on the output as keys, and
  the corresponding mail's key in the mail cache as values.
- 'date': last accessed date
- 'create_date': created date.  Removed after v1.1.7.
- 'create_dates': last up to ten created dates of same key
'''
mails_lists_cache = None

def list_output_cache_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'list_output_cache')

def args_to_lists_cache_key(args):
    dict_ = copy.deepcopy(args.__dict__)
    dict_['fetch'] = False
    dict_['stdout'] = False
    dict_['dim_old'] = None
    dict_['read_dates'] = False

    return json.dumps(dict_, sort_keys=True)

def get_mails_lists_cache():
    global mails_lists_cache

    if mails_lists_cache is None:
        if not os.path.isfile(list_output_cache_file_path()):
            mails_lists_cache = {}
        else:
            with open(list_output_cache_file_path(), 'r') as f:
                mails_lists_cache = json.load(f)
    if mails_lists_cache is None:
        mails_lists_cache = {}
    return mails_lists_cache

def writeback_list_output():
    cache = get_mails_lists_cache()
    with open(list_output_cache_file_path(), 'w') as f:
        json.dump(cache, f, indent=4)

def get_cached_list_outputs(key):
    cache = get_mails_lists_cache()
    if not key in cache:
        return None
    outputs = cache[key]
    # update last accessed date
    outputs['date'] = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    return outputs

def get_list_for(key):
    outputs = get_cached_list_outputs(key)
    if outputs is None:
        return None, None
    return outputs['output'], outputs['index_to_cache_key']

def get_cache_creation_dates(key):
    cache = get_mails_lists_cache()
    if not key in cache:
        return []
    outputs = cache[key]
    date_strs = []
    # 'create_dates' field has added after v1.1.7
    if 'create_dates' in outputs:
        date_strs = outputs['create_dates']
    # 'create_date' field has added after v1.1.6, removed after v1.1.7
    if 'create_date' in outputs:
        date_strs = [outputs['create_date']]
    return [datetime.datetime.strptime(s, '%Y-%m-%d-%H-%M-%S')
            for s in date_strs]

def get_cache_creation_date(key):
    cache = get_mails_lists_cache()
    if not key in cache:
        return None
    outputs = cache[key]
    # 'create_dates' field has added after v1.1.7
    if 'create_dates' in outputs:
        return datetime.datetime.strptime(
                outputs['create_dates'][-1], '%Y-%m-%d-%H-%M-%S')

    # 'create_date' field has added after v1.1.6, removed after v1.1.7
    if 'create_date' in outputs:
        return datetime.datetime.strptime(
                outputs['create_date'], '%Y-%m-%d-%H-%M-%S')
    return None

def get_last_mails_list():
    cache = get_mails_lists_cache()
    keys = [k for k in cache]
    key = sorted(keys, key=lambda x: cache[x]['date'])[-1]
    outputs = get_cached_list_outputs(key)
    if outputs is None:
        return None, None
    return outputs['output'], outputs['index_to_cache_key']

def get_last_list():
    cache = get_mails_lists_cache()
    keys = [k for k in cache if k != 'thread_output']
    key = sorted(keys, key=lambda x: cache[x]['date'])[-1]
    outputs = get_cached_list_outputs(key)
    if outputs is None:
        return None
    return outputs['output'], outputs['index_to_cache_key']

def get_last_thread():
    cache = get_mails_lists_cache()
    outputs = get_cached_list_outputs('thread_output')
    if outputs is None:
        return None
    return outputs['output'], outputs['index_to_cache_key']

def invalidate_cached_outputs(source):
    keys_to_del = []
    cache = get_mails_lists_cache()
    for key in cache.keys():
        try:
            key_dict = json.loads(key)
            if key_dict['source'] == source:
                keys_to_del.append(key)
        except:
            pass
    for key in keys_to_del:
        del cache[key]

def writeback_list_output_cache():
    cache = get_mails_lists_cache()
    with open(list_output_cache_file_path(), 'w') as f:
        json.dump(cache, f, indent=4)

def cache_list_str(key, list_str, mail_idx_key_map):
    cache = get_mails_lists_cache()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    create_dates = []
    if key in cache:
        last_cached = cache[key]
        # 'create_dates' field has added after v1.1.7
        if 'create_dates' in last_cached:
            create_dates = last_cached['create_dates'][-9:]
    create_dates.append(now_str)
    cache[key] = {
            'output': '\n'.join(['# (cached output)', list_str]),
            'index_to_cache_key': mail_idx_key_map,
            'date': now_str,        # last referenced date
            'create_dates': create_dates    # last up to ten create dates
            }
    max_cache_sz = 64
    if len(cache) == max_cache_sz:
        keys = sorted(cache.keys(), key=lambda x: cache[x]['date'])
        del cache[keys[0]]
    writeback_list_output_cache()

def get_mail(idx, not_thread_idx=False):
    cache = get_mails_lists_cache()
    sorted_keys = sorted(cache.keys(), key=lambda x: cache[x]['date'])
    if not_thread_idx and sorted_keys[-1] == 'thread_output':
        last_key = sorted_keys[-2]
    else:
        last_key = sorted_keys[-1]
    idx_to_keys = cache[last_key]['index_to_cache_key']
    idx_str = '%d' % idx
    if not idx_str in idx_to_keys:
        return None

    output_string_lines = cache[last_key]['output'].split('\n')
    if output_string_lines[0].startswith('# last reference: '):
        output_string_lines = output_string_lines[2:]
    output_string_lines = ['# last reference: %d' % idx,
                           '#'] + output_string_lines
    cache[last_key]['output'] = '\n'.join(output_string_lines)
    writeback_list_output()

    mail_key = idx_to_keys[idx_str]
    return hkml_cache.get_mail(key=mail_key)

def last_listed_mails():
    cache = get_mails_lists_cache()
    last_key = sorted(cache.keys(), key=lambda x: cache[x]['date'])[-1]
    idx_to_keys = cache[last_key]['index_to_cache_key']
    mails = []
    for idx in sorted([int(idx) for idx in idx_to_keys.keys()]):
        cache_key = idx_to_keys['%d' % idx]
        mail = hkml_cache.get_mail(key=cache_key)
        if mail is not None:
            mail.pridx = int(idx)
            mails.append(mail)
    return mails
