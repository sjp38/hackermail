# SPDX-License-Identifier: GPL-2.0

# bash completion support for hkml.
# To use this, 'source' this script.  For example,
#
#     $ source ./scripts/hkml-completion.sh
#     $ ./hkml [TAB][TAB]
#     list	write	patch	tag

_hkml_complete()
{
	local cur prev words cword
	_init_completion || return

	if [ "$cword" -lt 1 ]
	then
		return 1
	fi

	candidates=$("${words[0]}" --cli_complete "$cword" "${words[@]}")

	COMPREPLY=($(compgen -W "${candidates}" -- "$cur"))
	return 0
}

complete -F _hkml_complete hkml
