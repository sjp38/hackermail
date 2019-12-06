#!/bin/bash

if [ $# -lt 1 ]
then
	echo "Usage: $0 <lsmail options>"
	exit 1
fi

tmpfile=`mktemp`
./hkml.py ls $@ | python3 ./__format_reply.py > $tmpfile

vi $tmpfile
git send-email $tmpfile
rm $tmpfile
