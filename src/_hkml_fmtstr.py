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
    if nr_cols is None:
        return [line]
    words = line.split(' ')
    if prefix is not None:
        words = [prefix] + words
    lines = []
    line_words = []
    for w in words:
        line_words.append(w)
        line_len = len(' '.join(line_words))
        if line_len <= nr_cols:
            continue
        if len(line_words) == 1:
            lines.append(line_words[0])
        else:
            lines.append(' '.join(line_words[:-1]))
            if prefix is None:
                line_words = [line_words[-1]]
            else:
                line_words = [' ' * (len(prefix) + 1) + line_words[-1]]
    lines.append(' '.join(line_words))
    return lines
