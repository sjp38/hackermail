#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

def wrap_line(prefix, line, nr_cols):
    '''Wrap a string for a limited columns and returns a list of resulting
    lines.  Second and below lines starts with spaces of 'prefix' length.
    For example:
    >>> print('\n'.join(hkml_list.wrap_line('[something]', 'foo bar baz asdf', 20)))
    [something] foo bar
                baz asdf
    '''
    lines = []
    words = [prefix] + line.split(' ')
    words_to_print = []
    for w in words:
        words_to_print.append(w)
        line_len = len(' '.join(words_to_print))
        if nr_cols is not None and line_len > nr_cols:
            if len(words_to_print) == 1:
                lines.append(words_to_print[0])
            else:
                lines.append(' '.join(words_to_print[:-1]))
                words_to_print = [' ' * (len(prefix) + 1) + words_to_print[-1]]
    lines.append(' '.join(words_to_print))
    return lines
