#!/usr/bin/env python3

import sys

def format_reply(lines):
    head_fields = {}

    in_header = True
    for line in lines:
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
                if 'subject' in head_fields:
                    print("Subject: Re: %s" % head_fields['subject'])
                if 'message-id' in head_fields:
                    print("In-Reply-To: %s" % head_fields['message-id'])
                if 'cc' in head_fields:
                    print("Cc: %s" % head_fields['cc'])
                if 'from' in head_fields:
                    print("To: %s" % head_fields['from'])
                print("")
                print("On %s %s wrote:\n" % (head_fields['date'], head_fields['from']))
            continue
        line = line.strip()
        print("> %s" % line)

if __name__ == '__main__':
    format_reply(sys.stdin)
