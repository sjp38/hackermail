#!/usr/bin/env python3

import sys

for line in sys.stdin:
    # patch lines start with "[PATCH"
    line = line.strip()
    fields = line.split()
    if (fields[0] == "[PATCH]" or fields[1][0:2] == "0/" or
            fields[1][-1] == "]" or fields[2][0:2] == "0/"):
        print(line)
        continue
    print("\t", line)
