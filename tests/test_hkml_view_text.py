#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest
import os
import sys

bindir = os.path.dirname(os.path.realpath(__file__))
src_dir = os.path.join(bindir, '..', 'src')
sys.path.append(src_dir)

import hkml_view_text

class TestHkmlViewText(unittest.TestCase):
    def test_hunk_lines(self):
        # from 20241211203951.764733-2-joshua.hahnjy@gmail.com
        text = '''
@@ -4540,8 +4552,7 @@ int mem_cgroup_hugetlb_try_charge(struct mem_cgroup *memcg, gfp_t gfp,
         * but do not attempt to commit charge later (or cancel on error) either.
         */
        if (mem_cgroup_disabled() || !memcg ||
-               !cgroup_subsys_on_dfl(memory_cgrp_subsys) ||
-               !(cgrp_dfl_root.flags & CGRP_ROOT_MEMORY_HUGETLB_ACCOUNTING))
+               !cgroup_subsys_on_dfl(memory_cgrp_subsys) || !memcg_accounts_hugetlb())
                return -EOPNOTSUPP;

        if (try_charge(memcg, gfp, nr_pages))
--
2.43.5
'''
        text_lines = text.split('\n')
        hunk_indices = hkml_view_text.hunk_lines(text.split('\n'))
        self.assertEqual(hunk_indices, [[2, 11]])

if __name__ == '__main__':
    unittest.main()
