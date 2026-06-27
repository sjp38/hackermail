# SPDX-License-Identifier: GPL-2.0

import json
import os
import sys

import _hkml

'''
The file is a json format, having a list of strings.
'''
def config_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'config')

def read_config_file():
    if not os.path.isfile(config_file_path()):
        return {}
    with open(config_file_path(), 'r') as f:
        return json.load(f)

def write_config_file(config):
    with open(config_file_path(), 'w') as f:
        json.dump(config, f, indent=4, sort_keys=True)

def main(args):
    config = read_config_file()
    if args.action == 'set':
        config[args.name] = args.value
        write_config_file(config)
        return
    elif args.action == 'get':
        if args.name is None:
            for name in sorted(config.keys()):
                print('%s: %s' % (name, config[name]))
            return
        print('%s' % config[args.name])
        return
    elif args.action == 'remove':
        del config[args.name]
        write_config_file(config)
        return
    raise Exception("Bug!  Please report to hkml maintainer!")

def set_argparser(parser):
    parser.description = 'manage config'
    if sys.version_info >= (3,8):
        subparsers = parser.add_subparsers(
                title='action', dest='action', metavar='<action>',
                required=True)
    else:
        subparsers = parser.add_subparsers(
                title='action', dest='action', metavar='<action>')

    parsers_set = subparsers.add_parser('set', help='set config')
    parsers_set.add_argument('name', metavar='<name>', help='config name')
    parsers_set.add_argument('value', metavar='<value>', help='config value')

    parsers_get = subparsers.add_parser('get', help='get config')
    parsers_get.add_argument('name', metavar='<name>', nargs='?',
                             help='config name')

    parsers_remove = subparsers.add_parser('remove', help='remove config')
    parsers_remove.add_argument('name', metavar='<name>', help='config name')

