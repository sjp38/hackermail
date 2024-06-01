#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import curses

'''
Curses-based TUI viewer for hkml list output.
Menus:
  - recent mails
    - mailing lists
  - tags
  - custom queries

Shortcut from list
T: thread
  R: return to list
O: open
  T: tag
  R: return to thread or list
R: reply
F: forward
W: write new
?: help
'''

text_to_show = None

def __view(stdscr):
    focus_row = 0
    text_lines = text_to_show.split('\n')

    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    focus_color = curses.color_pair(1)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    normal_color = curses.color_pair(2)

    while True:
        stdscr.erase()
        scr_rows, scr_cols = stdscr.getmaxyx()
        start_row = max(int(focus_row - scr_rows / 2), 0)

        for row in range(scr_rows - 1):
            line_idx = start_row + row
            if line_idx >= len(text_lines):
                break
            if line_idx == focus_row:
                color = focus_color
            else:
                color = normal_color
            stdscr.addstr(row, 0, text_lines[line_idx], color)
        stdscr.addstr(scr_rows - 1, 0,
                      '# focus: %d/%d row' % (focus_row, scr_rows))

        x = stdscr.getch()
        c = chr(x)
        if c == 'j':
            focus_row = min(focus_row + 1, len(text_lines) - 1)
        elif c == 'k':
            focus_row = max(focus_row - 1, 0)
        elif c == 'q':
            break

def view(text):
    global text_to_show
    text_to_show = text
    curses.wrapper(__view)
