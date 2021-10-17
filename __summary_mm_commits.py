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
    removed = []
    for mail in mails:
        tokens = mail.split()[2:]
        if len(tokens) < 9:
            continue
        symbol = tokens[0]
        patch = tokens[1].split('.patch')[0]
        action = tokens[2:6]
        if action == ['added', 'to', '-mm', 'tree']:
            added.append(patch)
        if action == ['removed' 'from', '-mm', 'tree']:
            removed.append(patch)

    print('added patches')
    print('-------------')
    print()
    for patch in added:
        print(patch)

    print()
    print('removed patches')
    print('---------------')
    print()
    for patch in removed:
        print(patch)

    print()
    print('%d added, %d removed' % (len(added), len(removed)))

if __name__ == '__main__':
    main()
