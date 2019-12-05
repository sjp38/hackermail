#!/usr/bin/env python3

import sys

if len(sys.argv) != 2:
    print("Usage: %s <original plain mbox file>")

head_fields = {}

in_header = True
with open(sys.argv[1], 'r') as f:
        for line in f:
            if in_header:
                if line and line[0] in [' ', '\t'] and key:
                    head_fields[key] += ' %s' % line.strip()
                    continue
                line = line.strip()
                key = line.split(':')[0].lower()
                if key:
                    head_fields[key] = line[len(key) + 2:]
                elif line == '':
                    in_header = False
                    print("Subject: Re: %s" % head_fields['subject'])
                    print("In-Reply-To: %s" % head_fields['message-id'])
                    print("Cc: %s" % head_fields['cc'])
                    print("To: %s" % head_fields['from'])
                    print("")
                    print("On %s %s wrote:\n" % (head_fields['date'], head_fields['from']))
                continue
            line = line.strip()
            print(">%s" % line)
