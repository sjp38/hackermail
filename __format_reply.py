#!/usr/bin/env python3

import sys

if len(sys.argv) != 2:
    print("Usage: %s <original plain mbox file>")

head_fields = {}

in_header = True
with open(sys.argv[1], 'r') as f:
        for line in f:
            line = line.strip()
            if in_header:
                # TODO: handle multi line headers
                # e.g., Subject: aasdf
                #        asdgag
                key = line.split(':')[0].lower()
                if key:
                    head_fields[key] = line[len(key) + 2:]
                elif line == '':
                    in_header = False
                    print("Subject: Re: %s" % head_fields['subject'])
                    print("In-Reply-To: %s" % head_fields['message-id'])
                    print("")
                    print("On %s %s wrote:\n" % (head_fields['date'], head_fields['from']))
                continue
            print(">%s" % line)
