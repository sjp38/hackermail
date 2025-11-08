#!/bin/bash
# SPDX-License-Identifier: GPL-2.0


bindir=$(dirname "$0")
python_binary="python3"

if [ "$1" == "coverage" ]; then

	if ! python3 -m coverage help &> /dev/null
	then
		echo "coverage not found, install it (e.g., 'pip3 install coverage')" >&2
		exit 1
	fi

	python3 -m coverage erase
	python_binary="python3 -m coverage run -a"
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
	python3 -m coverage xml
	python3 -m coverage report
fi

for script in codespell.sh flake8.sh
do
	if "$bindir/$script"
	then
		echo "PASS $script"
	else
		echo "FAIL $script"
		exit 1
	fi
done
