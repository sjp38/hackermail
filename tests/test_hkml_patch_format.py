#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest
import os
import sys

bindir = os.path.dirname(os.path.realpath(__file__))
src_dir = os.path.join(bindir, '..', 'src')
sys.path.append(src_dir)

import hkml_patch_format

class TestHkmlPatchFormat(unittest.TestCase):
    def assert_parse_subject_prefix(self, prefix, expect_success, expects):
        invalid_reason, is_rfc, version_nr, sequence, target_tree = \
                hkml_patch_format.parse_subject_prefix(prefix)
        if expect_success:
            self.assertTrue(invalid_reason == None)
        else:
            self.assertTrue(invalid_reason != None)
        self.assertEqual([is_rfc, version_nr, sequence, target_tree], expects)

    def test_parse_subject_prefix(self):
        self.assert_parse_subject_prefix('RFC PATCH', True,
                                         [True, None, None, None])
        self.assert_parse_subject_prefix('PATCH v2', True,
                                         [False, 'v2', None, None])
        self.assert_parse_subject_prefix('PATCH v2 00/12', True,
                                         [False, 'v2', '00/12', None])
        self.assert_parse_subject_prefix('PATCH v2 03/12', True,
                                         [False, 'v2', '03/12', None])
        self.assert_parse_subject_prefix('PATCH v2 mm-unstable', True,
                                         [False, 'v2', None, 'mm-unstable'])
        self.assert_parse_subject_prefix('PATCH v2 mm-unstable 03/12', True,
                                         [False, 'v2', '03/12', 'mm-unstable'])
        self.assert_parse_subject_prefix('PATCH 6.12.y', True,
                                         [False, None, None, '6.12.y'])
        self.assert_parse_subject_prefix('PATCH 6.12.y v3', True,
                                         [False, 'v3', None, '6.12.y'])

        fail_expects = [None, None, None, None]
        self.assert_parse_subject_prefix('foo', False, fail_expects)
        self.assert_parse_subject_prefix('RFC foo', False, fail_expects)
        self.assert_parse_subject_prefix('foo v2', False, fail_expects)
        # multiple sequence
        self.assert_parse_subject_prefix('PATCH 03/12 04/12', False,
                                         fail_expects)
        self.assert_parse_subject_prefix('PATCH 6.12.y foo', False,
                                         fail_expects)
        self.assert_parse_subject_prefix('PATCH v2 v4', False, fail_expects)

if __name__ == '__main__':
    unittest.main()
