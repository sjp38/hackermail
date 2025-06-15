#!/bin/bash
# SPDX-License-Identifier: GPL-2.0


bindir=$(dirname "$0")
python_binary="python3"

if [ "$1" == "coverage" ]; then

        if [ -z "$(which coverage 2>/dev/null)" ]; then
                echo "coverage not found, install it with 'pip3 install coverage'" >&2
                exit 1
        fi

        coverage erase
        python_binary="coverage run -a"
fi

for test_file in "$bindir"/test_*.py
do
        if $python_binary "$test_file" &> /dev/null
        then
                echo "PASS unit $(basename $test_file)"
        else
                echo "FAIL unit $(basename $test_file)"
                exit 1
        fi
done

if [ "$1" == "coverage" ]; then
        coverage xml
        coverage report
fi
