#!/usr/bin/env python3

import sys

for line in sys.stdin:
    # Each line should start with a subject of a patch mail
    #       [PATCH], [PATCH v2], [PATCH 1/3], [PATCH v2 0/2], ...
    line = line.strip()
    fields = line.split(']')[0][1:].split()
    series_idx = fields[-1].split('/')[0]
    if series_idx.isdigit() and int(series_idx) != 0:
        line = "\t" + line
    print(line)
