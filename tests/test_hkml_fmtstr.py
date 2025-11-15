#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest
import os
import sys

bindir = os.path.dirname(os.path.realpath(__file__))
src_dir = os.path.join(bindir, '..', 'src')
sys.path.append(src_dir)

import _hkml_fmtstr

class TestHkmlFmtstr(unittest.TestCase):
    def test_wrap_line(self):
        self.assertEqual(
                _hkml_fmtstr.wrap_line('[something]', 'foo bar baz asdf', 20),
                ['[something] foo bar',
                 '            baz asdf',
                 ])
        self.assertEqual(
                _hkml_fmtstr.wrap_line(None, 'foo bar baz asdf', 15),
                ['foo bar baz',
                 'asdf'])

if __name__ == '__main__':
    unittest.main()
