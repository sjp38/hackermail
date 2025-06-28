#!/bin/bash
# SPDX-License-Identifier: GPL-2.0

set -e

bindir=$(dirname "$0")
# this file is at /tests/ of the repo
src_dir="$bindir/../src/"

if ! which codespell
then
	echo "codespell not found.  skip"
	exit 0
fi

if ! codespell "$src_dir" --ignore-regex "damon"
then
	echo "codespell failed"
	exit 1
fi
