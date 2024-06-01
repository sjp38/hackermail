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

def display(scr, lines, focus_row, focus_color, normal_color):
    scr.erase()
    scr_rows, scr_cols = scr.getmaxyx()
    start_row = max(int(focus_row - scr_rows / 2), 0)

    for row in range(scr_rows - 1):
        line_idx = start_row + row
        if line_idx >= len(lines):
            break
        if line_idx == focus_row:
            color = focus_color
        else:
            color = normal_color
        scr.addstr(row, 0, lines[line_idx], color)
    scr.addstr(scr_rows - 1, 0,
               '# focus: %d/%d row' % (focus_row, scr_rows))

def __view(stdscr):
    focus_row = 0
    text_lines = text_to_show.split('\n')

    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    focus_color = curses.color_pair(1)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    normal_color = curses.color_pair(2)

    while True:
        display(stdscr, text_lines, focus_row, focus_color, normal_color)

        x = stdscr.getch()
        c = chr(x)
        if c == 'j':
            focus_row = min(focus_row + 1, len(text_lines) - 1)
        elif c == 'k':
            focus_row = max(focus_row - 1, 0)
        elif c == 'q':
            break
        elif c == '?':
            display(stdscr, [
                'j: move focus down',
                'k: move focus up',
                'q: quit',
                '?: show this',
                '',
                'Press any key to return'], 0, focus_color, normal_color)
            stdscr.refresh()
            x = stdscr.getch()

def view(text):
    global text_to_show
    text_to_show = text
    curses.wrapper(__view)
