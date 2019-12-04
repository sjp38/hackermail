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
                key = line.split(':')[0]
                if key.lower() == 'subject':
                    subject = line[len(key) + 2:]
                    continue
                if key.lower() == 'message-id':
                    msgid = line[len(key) + 2:]
                    continue
                if key.lower() == 'date':
                    date = line[len(key) + 2:]
                    continue
                if key.lower() == 'from':
                    sender = line[len(key) + 2:]
                    continue
                if line == '':
                    is_header = False
                    print("Subject: Re: %s" % subject)
                    print("In-Reply-To: %s" % msgid)
                    print("")
                    print("On %s %s wrote:" % (date, sender))
                    continue
                continue
            print(">%s" % line)
