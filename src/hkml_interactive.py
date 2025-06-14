# SPDX-License-Identifier: GPL-2.0


def main(args):
    print("Under construction")
    print('Please use "hkml -h" to get some guidance')
    exit(1)
    print("What to do?")
    print("1: List mails")
    print("2: Fetch mails")
    print("3: Write mail")
    print("4: Synchronize remote backup")
    print("5: Show tags")
    print("6: Manage mails cache")
    try:
        answer = int(input("Select: "))
    except:
        print("wrong answer")
        exit(1)

    if answer == 1:
        print("Type of mails source")
        print("1: Mailing list")
        print("2: Thread of a mail")
        print("3: Mbox file")
