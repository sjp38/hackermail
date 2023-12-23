#!/bin/bash

pr_usage()
{
	echo "Usage: $0 [OPTION]... [duration in days]"
	echo
	echo "OPTION"
	echo "  -h, --help	Show this message"
}

function pr_usage_exit {
	exit_code=$1
	pr_usage
	exit "$exit_code"
}

duration_days=7

while [ $# -ne 0 ]
do
	case $1 in
	"--help" | "-h")
		pr_usage_exit 0
		;;
	*)
		if [ $# -ne 1 ]
		then
			pr_usage_exit 1
		fi
		duration_days=$1
		break
		;;
	esac
done

since=$(date --date="-$duration_days day" +%Y-%m-%d)

bindir=$(dirname "$0")

"$bindir/hkml" read mm-commits -cn --since "$since" --fetch | \
	"$bindir/__summary_mm_commits.py"
