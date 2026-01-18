# SPDX-License-Identifier: GPL-2.0

import sys

def handle_cli_complete():
    cword = int(sys.argv[2])
    words = sys.argv[3:]
    if cword == 0:
        return
    candidates = []
    if cword == 1:
        candidates = ['list', 'write', 'patch', 'tag']
    candidates.append('--help')
    print(' '.join(candidates))
