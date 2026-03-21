#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

'''
https://sashiko.dev provides AI review results of kernel patches.  Fetch the
results and show those on the terminal.
'''

import argparse

requests_import_success = False

try:
    import requests
    requests_import_success = True
except:
    pass

class SashikoDevReview:
    result = None
    status = None
    patch_msgid = None
    patch_subject = None
    inline_review = None

    def __init__(self, result, status, patch_msgid, patch_subject,
                 inline_review):
        self.result = result
        self.status = status
        self.patch_msgid = patch_msgid
        self.patch_subject = patch_subject
        self.inline_review = inline_review

msgid_output_cache = {}
session = None

def get_review(msgid):
    '''
    Return SashikoDevReview and an error
    '''
    if requests_import_success is False:
        # TODO: add more guide about how to install the module
        return None, 'requests python module import fail'

    if msgid in msgid_output_cache:
        return msgid_output_cache[msgid], None

    global session
    if session is None:
        session = requests.session()
        session.headers.update({'User-Agent': 'hkml/1.5.4'})
    resp = session.get('https://sashiko.dev/api/patch',
                       params={'id': msgid}, timeout=10)
    if resp.status_code != 200:
        return None, 'get response is not 200 but %s' % resp.status_code
    data = resp.json()

    id_patch_map = {}
    for patch in data['patches']:
        id_patch_map[patch['id']] = patch

    for idx, review in enumerate(data['reviews']):
        result = review['result']
        status = review['status']
        patch_id = review['patch_id']
        patch = id_patch_map[patch_id]
        patch_msgid = patch['message_id']
        patch_subject = patch['subject']
        inline_review = review['inline_review']

        sashiko_dev_review = SashikoDevReview(
                result, status, patch_msgid, patch_subject, inline_review)
        msgid_output_cache[patch_msgid] = sashiko_dev_review
    if msgid in msgid_output_cache:
        return msgid_output_cache[msgid], None
    return None, 'no review found'
