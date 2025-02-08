#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest
import os
import sys

bindir = os.path.dirname(os.path.realpath(__file__))
src_dir = os.path.join(bindir, '..', 'src')
sys.path.append(src_dir)

import hkml_view

class TestHkmlViewText(unittest.TestCase):
    def test_tabs_to_spaces(self):
        self.assertEqual(
                hkml_view.tabs_to_spaces('01234567\t123\t1', 8),
                '01234567        123     1')

if __name__ == '__main__':
    unittest.main()
