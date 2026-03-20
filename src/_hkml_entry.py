#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

def main():
    import runpy
    runpy.run_module('hkml', run_name='__main__', alter_sys=True)
