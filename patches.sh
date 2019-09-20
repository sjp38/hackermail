#!/bin/bash

if [ $# -gt 0 ]
then
	SINCE=$1
fi

if [ $# -gt 1 ]
then
	UNTIL=$2
fi

if [ $SINCE != "" ]
then
	OPT="--since $SINCE "
fi

if [ $UNTIL != "" ]
then
	OPT=$OPT"--until $UNTIL"
fi

git log --pretty="%s (%h) %cd" $OPT | grep -e "^\[PATCH*"
