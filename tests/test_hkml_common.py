#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import datetime
import os
import sys
import unittest

bindir = os.path.dirname(os.path.realpath(__file__))
src_dir = os.path.join(bindir, "..", "src")
sys.path.append(src_dir)

import hkml_common


class TestHkmlCommon(unittest.TestCase):
    def test_parse_date_diff_input(self):
        now = datetime.datetime(2025, 5, 31, 10, 18)
        self.assertEqual(
            hkml_common.parse_date_diff("-2 days", now),
            datetime.datetime(2025, 5, 29, 10, 18),
        )
        self.assertEqual(
            hkml_common.parse_date_diff("+1 days", now),
            datetime.datetime(2025, 6, 1, 10, 18),
        )


if __name__ == "__main__":
    unittest.main()
