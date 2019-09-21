#!/bin/bash

if [ $# -lt 1 ]
then
	echo "Usage: $0 <since date> [end date]"
	exit 1
fi

BINDIR=`dirname $0`

SINCE=$1

if [ $# -gt 1 ]
then
	UNTIL=$2
fi

OPT="--since $SINCE "

if [ $UNTIL ]
then
	OPT=$OPT"--until $UNTIL"
fi

git log --pretty="%s (%h) %cd" $OPT | grep -e "^\[PATCH*" | $BINDIR/_indent_patches.py
