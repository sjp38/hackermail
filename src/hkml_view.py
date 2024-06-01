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
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    focus_color = curses.color_pair(1)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    normal_color = curses.color_pair(2)

    stdscr.clear()
    while True:
        rows, cols = stdscr.getmaxyx()
        for idx, line in enumerate(text_to_show.split('\n')):
            if idx == focus_row:
                color = focus_color
            else:
                color = normal_color
            stdscr.addstr(idx, 0, line, color)
            if idx == rows - 1:
                break
        x = stdscr.getch()

def view(text):
    global text_to_show
    text_to_show = text
    curses.wrapper(__view)
