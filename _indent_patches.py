#!/usr/bin/env python3

import sys

for line in sys.stdin:
    # patch lines start with "[PATCH"
    line = line.strip()
    fields = line.split(']')[0][1:].split() # e.g., PATCH, PATCH v2, PATCH 1/3
    series_idx = fields[-1].split('/')[0]
    if series_idx.isdigit() and int(series_idx) != 0:
        line = "\t" + line
    print(line)
