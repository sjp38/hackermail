#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import sys
import unittest

bindir = os.path.dirname(os.path.realpath(__file__))
src_dir = os.path.join(bindir, "..", "src")
sys.path.append(src_dir)

import hkml_view_mails


class TestHkmlViewText(unittest.TestCase):
    def test_get_files_for_reviewer(self):
        maintainers_file_content = """
DATA ACCESS MONITOR
M:	SeongJae Park <sj@kernel.org>
L:	damon@lists.linux.dev
L:	linux-mm@kvack.org
S:	Maintained
W:	https://damonitor.github.io
P:	Documentation/mm/damon/maintainer-profile.rst
T:	git git://git.kernel.org/pub/scm/linux/kernel/git/akpm/mm
T:	quilt git://git.kernel.org/pub/scm/linux/kernel/git/akpm/25-new
T:	git git://git.kernel.org/pub/scm/linux/kernel/git/sj/linux.git damon/next
F:	Documentation/ABI/testing/sysfs-kernel-mm-damon
F:	Documentation/admin-guide/mm/damon/
F:	Documentation/mm/damon/
F:	include/linux/damon.h
F:	include/trace/events/damon.h
F:	mm/damon/
F:	samples/damon/
F:	tools/testing/selftests/damon/

DAVICOM FAST ETHERNET (DMFE) NETWORK DRIVER
L:	netdev@vger.kernel.org
S:	Orphan
F:	Documentation/networking/device_drivers/ethernet/dec/dmfe.rst
F:	drivers/net/ethernet/dec/tulip/dmfe.c
"""
        self.assertEqual(
            hkml_view_mails.get_files_for_reviewer(
                "SeongJae Park <sj@kernel.org>", maintainers_file_content
            ),
            [
                "Documentation/ABI/testing/sysfs-kernel-mm-damon",
                "Documentation/admin-guide/mm/damon/",
                "Documentation/mm/damon/",
                "include/linux/damon.h",
                "include/trace/events/damon.h",
                "mm/damon/",
                "samples/damon/",
                "tools/testing/selftests/damon/",
            ],
        )


if __name__ == "__main__":
    unittest.main()
