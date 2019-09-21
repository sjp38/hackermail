#!/usr/bin/env python3

import sys

for line in sys.stdin:
    # patch lines start with "[PATCH"
    line = line.strip()
    fields = line.split()
    if (fields[0] == "[PATCH]" or       # Single patch
            fields[1][-1] == "]" or     # Versioned single patch,
                                        #  e.g., [PATCH v2]
            fields[1][0:2] == "0/" or   # First patch in series
                                        #  e.g., [PATCH 0/3]
            fields[2][0:2] == "0/"):    # First patch in versioned series
                                        #  e.g., [PATCH v2 0/3]
        print(line)
        continue
    print("\t", line)
