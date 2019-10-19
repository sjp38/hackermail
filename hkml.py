#!/usr/bin/env python3

import argparse
import lsmails
import fetchmails

class SubCmdHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_action(self, action):
        parts = super(argparse.RawDescriptionHelpFormatter,
                self)._format_action(action)
        # Skips subparsers help
        if action.nargs == argparse.PARSER:
            parts = '\n'.join(parts.split('\n')[1:])
        return parts

parser = argparse.ArgumentParser(formatter_class=SubCmdHelpFormatter)
subparsers = parser.add_subparsers(title='command', dest='command',
        metavar='<command>')

parser_ls = subparsers.add_parser('ls', help = 'list mails')
lsmails.set_argparser(parser_ls)

parser_fetch = subparsers.add_parser('fetch', help = 'fetch mails')
fetchmails.set_argparser(parser_fetch)

args = parser.parse_args()

if not args.command:
    parser.print_help()
    exit(1)

if args.command == 'ls':
    lsmails.main(args)
elif args.command == 'fetch':
    fetchmails.main(args)
