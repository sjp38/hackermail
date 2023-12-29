#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os

def set_argparser(parser=None):
    parser.add_argument('--manifest', metavar='<file>',
            help='manifest file to use')

def main(args=None):
    if args == None:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    os.mkdir('.hkm')
    os.mkdir('.hkm/archives')

    if args.manifest != None:
        if not os.path.isfile(args.manifest):
            print('--manifest (%s) not found' % args.manifest)
            exit(1)
        with open(args.manifest, 'r') as f:
            content = f.read()
        with open(os.path.join('.hkm', 'manifest'), 'w') as f:
            f.write(content)

if __name__ == '__main__':
    main()
