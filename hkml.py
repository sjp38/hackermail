#!/usr/bin/env python3

import argparse
import lsmails

class SubCmdHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_action(self, action):
        parts = super(argparse.RawDescriptionHelpFormatter,
                self)._format_action(action)
        # Skips subparsers help
        if action.nargs == argparse.PARSER:
            parts = '\n'.join(parts.split('\n')[1:])
        return parts

parser = argparse.ArgumentParser(formatter_class=SubCmdHelpFormatter)
subparsers = parser.add_subparsers(title='command', dest='command', metavar='')

parser_ls = subparsers.add_parser('ls', help = 'list mails')
lsmails.set_argparser(parser_ls)

args = parser.parse_args()

if not args.command:
    parser.print_help()
    exit(1)

if args.command == 'ls':
    lsmails.main(args)
