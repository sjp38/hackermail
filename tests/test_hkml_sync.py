
#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest
from unittest.mock import patch
import os
import sys

bindir = os.path.dirname(os.path.realpath(__file__))
src_dir = os.path.join(bindir, '..', 'src')
sys.path.append(src_dir)

import hkml_sync

class TestHkmlSync(unittest.TestCase):
    @patch('hkml_sync.exit', side_effect=SystemExit)
    def test_setup_git_remote_none(self, mock_exit):
        with self.assertRaises(SystemExit):
            hkml_sync.setup_git('test', None)
    @patch('hkml_sync.subprocess.call')
    @patch('hkml_sync.exit', side_effect=SystemExit)
    def test_setup_git_init_fails(self, mock_call, mock_exit):
        mock_call.return_value = 1
        with self.assertRaises(SystemExit):
            hkml_sync.setup_git('test', 'test')
        
if __name__ == '__main__':
    unittest.main()
