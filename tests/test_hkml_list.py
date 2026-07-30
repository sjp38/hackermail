#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

bindir = os.path.dirname(os.path.realpath(__file__))
src_dir = os.path.join(bindir, '..', 'src')
sys.path.append(src_dir)

import _hkml_list_cache
import hkml_list


class FakeMail:
    def __init__(self, msgid):
        self.msgid = msgid

    def get_msgid(self):
        return self.msgid


class TestHkmlList(unittest.TestCase):
    def test_add_msgid_location_comment(self):
        mail_items = [
                SimpleNamespace(mail=FakeMail('<first@example.com>')),
                SimpleNamespace(mail=FakeMail('<second@example.com>')),
                SimpleNamespace(mail=FakeMail('<target@example.com>')),
                ]
        list_data = hkml_list.MailsListData(
                '# one stat line\nfirst\nsecond\ntarget',
                len_comments=1,
                mail_items=mail_items,
                line_nr_mail_idx_map={0: 0, 1: 1, 2: 2})

        hkml_list.add_msgid_location_comment(
                list_data, 'target@example.com')

        self.assertEqual(
                list_data.comments_lines[-1],
                '# mail of the msgid is at row 5, mail index 2 '
                '(target ...)')
        self.assertEqual(list_data.text.splitlines()[4], 'target')

    def test_cache_keeps_msgid_location_comment(self):
        list_data = hkml_list.MailsListData(
                '# one stat line\n'
                '# mail of the msgid is at row 5, mail index 2 '
                '(target ...)\n'
                'first\nsecond\ntarget',
                len_comments=2,
                mail_items=[],
                line_nr_mail_idx_map={})
        cache = {}

        with patch.object(
                _hkml_list_cache, 'get_mails_lists_cache',
                return_value=cache), \
             patch.object(_hkml_list_cache, 'writeback_list_output'), \
             patch.object(_hkml_list_cache, 'record_cache_creation'):
            _hkml_list_cache.set_item('key', list_data)

        self.assertIn(
                '# mail of the msgid is at row 6, mail index 2 '
                '(target ...)',
                cache['key']['output'])
        self.assertNotIn(
                '# mail of the msgid is at row 5, mail index 2 '
                '(target ...)',
                cache['key']['output'])


if __name__ == '__main__':
    unittest.main()
