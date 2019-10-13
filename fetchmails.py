#!/usr/bin/env python3

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--manifest', '-m', type=str,
        default='.configs/manifest.js',
        help='Manifesto file in grok\'s format')
parser.add_argument('lists', type=str, nargs='+',
        help='Name of the mailing list')

args = parser.parse_args()
manifest = args.manifest
mail_lists = args.lists

print(manifest, mail_lists)
