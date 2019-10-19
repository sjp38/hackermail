#!/usr/bin/env python3

import argparse
import lsmails

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(title='command', dest='command', help='sub parser help')

parser_ls = subparsers.add_parser('ls', help = 'list mails')
lsmails.set_argparser(parser_ls)
# parser_ls.set_defaults(func=lsmails.main)

args = parser.parse_args()

if not args.command:
    parser.print_help()
    exit(1)

if args.command == 'ls':
    lsmails.main(args)
