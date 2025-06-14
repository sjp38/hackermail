#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import sys
import unittest

bindir = os.path.dirname(os.path.realpath(__file__))
src_dir = os.path.join(bindir, "..", "src")
sys.path.append(src_dir)

import hkml_view


class TestHkmlViewText(unittest.TestCase):
    def test_tabs_to_spaces(self):
        self.assertEqual(
            hkml_view.tabs_to_spaces("01234567\t123\t1", 8), "01234567        123     1"
        )

    def test_wrap_text(self):
        self.assertEqual(
            hkml_view.wrap_text(["0123 567 9abcd"], 9), ["0123 567", "9abcd"]
        )
        self.assertEqual(hkml_view.wrap_text(["0123456789abcd"], 5), ["0123456789abcd"])
        self.assertEqual(hkml_view.wrap_text([""], 5), [""])
        self.assertEqual(hkml_view.wrap_text(["  ab"], 5), ["  ab"])
        self.assertEqual(hkml_view.wrap_text(["> abc def"], 5), ["> abc", "> def"])


if __name__ == "__main__":
    unittest.main()
