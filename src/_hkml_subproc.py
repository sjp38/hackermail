# SPDX-License-Identifier: GPL-2.0

# Common subprocess usage helpers

import subprocess

def cmd_available(cmd):
    try:
        subprocess.check_output(['which', cmd], stderr=subprocess.DEVNULL)
        return True
    except:
        return False
