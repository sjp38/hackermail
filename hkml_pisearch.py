# SPDX-License-Identifier: GPL-2.0

'''
Experimental.  Search public-inbox.
'''

import subprocess
import xml.etree.ElementTree as ET

import _hkml

def tagname(node):
    return node.tag[len('{http://www.w3.org/2005/Atom}'):]

def parse_entry(entry):
    parsed = {}
    for node in entry:
        if tagname(node) == 'author':
            for child in node:
                parsed['author.%s' % tagname(child)] = child.text
        elif tagname(node) in ['title', 'updated']:
            parsed[tagname(node)] = node.text
        elif tagname(node) == 'link':
            parsed['link'] = node.attrib['href']
    return parsed

def main(args):
    manifest = _hkml.get_manifest()
    pi_url = manifest['site']
    query_url = '%s/%s/?q=%s&x=A' % (pi_url, args.mailing_list, args.query)
    print(query_url)
    query_output = 'lore_search.xml'
    if subprocess.call(['curl', query_url, '-o', query_output]) != 0:
        print('fetching query result failed')
        exit(1)
    try:
        tree = ET.parse(query_output)
    except:
        print('parsing atom feed failed')
        exit(1)
    root = tree.getroot()
    entries = [parse_entry(child) for child in root
             if tagname(child) == 'entry']
    for entry in entries:
        for k, v in entry.items():
            print('%s: %s' % (k, v))
        print()

def set_argparser(parser):
    parser.add_argument('mailing_list', help='mailing list to query')
    parser.add_argument('query', help='public inbox query string')
