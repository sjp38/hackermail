#!/usr/bin/env python3

import argparse
import os

def set_argparser(parser=None):
    pass

def main(args=None):
    if args == None:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    os.mkdir('.hkm')
    os.mkdir('.hkm/archives')

if __name__ == '__main__':
    main()
