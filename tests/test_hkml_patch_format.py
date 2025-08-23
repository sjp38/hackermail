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
    def assert_is_valid_subject_prefix(self, prefix, is_valid, invalid_reason):
        is_valid_, invalid_reason_ = hkml_patch_format.is_valid_subject_prefix(
                prefix)
        self.assertEqual(is_valid, is_valid_)
        self.assertEqual(invalid_reason, invalid_reason_)

    def test_is_valid_subject_prefix(self):
        self.assert_is_valid_subject_prefix('RFC PATCH', True, None)

if __name__ == '__main__':
    unittest.main()
