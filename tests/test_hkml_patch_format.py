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
    def test_is_valid_subject_prefix(self):
        is_valid, invalid_reason = hkml_patch_format.is_valid_subject_prefix(
                'RFC PATCH')
        self.assertTrue(is_valid)

if __name__ == '__main__':
    unittest.main()
