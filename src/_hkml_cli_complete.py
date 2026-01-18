# SPDX-License-Identifier: GPL-2.0

import sys

def prev_option_nr_filed_args(words, cword):
    for i in range(cword -1, -1, -1):
        if words[i].startswith('-'):
            prev_option = words[i]
            nr_filled_args = cword - 1 - i
            return prev_option, nr_filled_args
    return None, None

def should_show_options(words, cword, option_nr_args):
    '''
    words and cword should start from the options part (no command)
    option_nr_args is option name to their required number of arguments map.
    For variable number of options, -1 is given.
    '''
    if cword == 0 or words[cword].startswith('-'):
        return True

    if words[cword - 1] == '--monitoring_intervals_autotune':
        return True

    prev_option, nr_filled_args = prev_option_nr_filed_args(words, cword)
    if prev_option is None:
        return False
    if not prev_option in option_nr_args:
        return False
    return option_nr_args[prev_option] == nr_filled_args

def option_candidates(words, cword, option_nr_args):
    '''
    words and cword should start from the options part (no command)
    option_nr_args is option name to their required number of arguments map.
    For variable number of options, -1 is given.
    '''
    if should_show_options(words, cword, option_nr_args):
        return list(option_nr_args.keys())
    return []

def list_candidates(words, cword):
    candidates = option_candidates(words, cword, {
        '--since': 1, '--until': 1})
    if candidates:
        return candidates
    return []

def patch_format_candidates(words, cword):
    return option_candidates(words, cword, {
        '--output_dir': 1,
        '--rfc': 0,
        '--subject_prefix': 1,
        '--to': -1,
        '--cc': -1,
        })

def patch_candidates(words, cword):
    if cword == 0:
        return ['format', 'commit_cv']
    if cword >= 1 and words[0] == 'format':
        return patch_format_candidates(words[1:], cword - 1)
    return []

def handle_cli_complete():
    cword = int(sys.argv[2])
    words = sys.argv[3:]
    if cword == 0:
        return
    candidates = []
    if cword == 1:
        candidates = ['list', 'write', 'patch', 'tag']
    if cword > 1:
        command = words[1]
        if command == 'list':
            candidates = list_candidates(words[2:], cword - 2)
        elif command == 'patch':
            candidates = patch_candidates(words[2:], cword - 2)
    if not '--help' in words:
        candidates.append('--help')
    print(' '.join(candidates))
