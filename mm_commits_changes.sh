#!/bin/bash

if [ $# -eq 1 ]
then
	duration_days=$1
else
	duration_days=7
fi
since=$(date --date="-$duration_days day" +%Y-%m-%d)

bindir=$(dirname "$0")

"$bindir/hkml" ls mm-commits -cn --since "$since" | \
	"$bindir/__summary_mm_commits.py" | less
