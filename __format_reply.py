#!/usr/bin/env python3

import sys

if len(sys.argv) != 2:
    print("Usage: %s <original plain mbox file>")

is_header = True
subject = None
msgid = None
date = None
sender = None
with open(sys.argv[1], 'r') as f:
        for line in f:
            line = line.strip()
            if is_header:
                key = line.split(':')[0].lower()
                # TODO: handle multi line headers
                # e.g., Subject: aasdf
                #        asdgag
                if key == 'subject':
                    subject = line[len(key) + 2:]
                elif key == 'message-id':
                    msgid = line[len(key) + 2:]
                elif key == 'date':
                    date = line[len(key) + 2:]
                elif key == 'from':
                    sender = line[len(key) + 2:]
                elif line == '':
                    is_header = False
                    print("Subject: Re: %s" % subject)
                    print("In-Reply-To: %s" % msgid)
                    print("")
                    print("On %s %s wrote:" % (date, sender))
                continue
            print(">%s" % line)
