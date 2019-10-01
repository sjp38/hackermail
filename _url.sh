#!/bin/bash

if [ $# -lt 1 ]
then
	echo "Usage: $0 <git hash> [git dir]"
	exit 1
fi

HASH=$1

if [ $# -gt 1 ]
then
	GDIR=$2
fi

if [ -z "$GDIR" ]
then
	GDIR="./.git"
fi

MSGID=$(git --git-dir=$GDIR show $HASH:m | grep -i -e "^Message-ID: " | \
	awk -e '{print substr($2, 2, length($2) - 2)}')
echo https://lkml.kernel.org/r/$MSGID
