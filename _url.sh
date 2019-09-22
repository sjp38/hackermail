#!/bin/bash

if [ $# -ne 1 ]
then
	echo "Usage: $0 <git hash>"
	exit 1
fi

HASH=$1

MSGID=$(git show $HASH:m | grep -e "^Message-Id: " | \
	awk -e '{print substr($2, 2, length($2) - 2)}')
echo https://lkml.kernel.org/r/$MSGID
