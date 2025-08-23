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
    def assert_is_valid_subject_prefix(self, prefix, is_valid):
        is_valid_, invalid_reason_ = hkml_patch_format.is_valid_subject_prefix(
                prefix)
        self.assertEqual(is_valid, is_valid_)

    def test_is_valid_subject_prefix(self):
        self.assert_is_valid_subject_prefix('RFC PATCH', True)
        self.assert_is_valid_subject_prefix('PATCH v2', True)
        self.assert_is_valid_subject_prefix('PATCH v2 mm-unstable', True)
        self.assert_is_valid_subject_prefix('PATCH 6.12.y', True)

if __name__ == '__main__':
    unittest.main()
