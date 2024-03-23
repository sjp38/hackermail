# SPDX-License-Identifier: GPL-2.0

'''
Synchronize personal files in .hkm/ via user-specified git repo.
'''

def main(args):
    print(args)

def set_argparser(parser):
    parser.description = 'synchronize the outputs and setups'
    parser.add_argument('--remote', metavar='<git repo>',
                        help='remote git repo to synchronize with')
