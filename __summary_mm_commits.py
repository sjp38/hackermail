#!/usr/bin/env python3

import sys

def main():
    msg = sys.stdin.read()
    mails = []
    mail = ''
    for line in msg.split('\n'):
        if not line.startswith(' '):
            if mail != '':
                mails.append(mail)
            mail = ''
        mail = ' '.join([mail, line.strip()])
    if mail != '':
        mails.append(mail)

    added = []
    for mail in mails:
        tokens = mail.split()[2:]
        if len(tokens) < 9:
            continue
        symbol = tokens[0]
        patch = tokens[1]
        action = tokens[2:5]
        if action == ['added', 'to', '-mm']:
            added.append(patch)

    print('added patches')
    for patch in added:
        print(patch)

if __name__ == '__main__':
    main()
