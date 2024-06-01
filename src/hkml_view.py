#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import curses

import hkml_list
import hkml_open

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

class ScrollableList:
    screen = None
    lines = None
    focus_row = None
    focus_color = None
    normal_color = None
    input_handler = None

    def __init__(self, screen, lines, focus_row, focus_color, normal_color,
                 input_handler):
        self.screen = screen
        self.lines = lines
        self.focus_row = focus_row
        self.focus_color = focus_color
        self.normal_color = normal_color
        self.input_handler = input_handler

    def __draw(self):
        self.screen.erase()
        scr_rows, scr_cols = self.screen.getmaxyx()
        start_row = max(int(self.focus_row - scr_rows / 2), 0)

        for row in range(scr_rows - 1):
            line_idx = start_row + row
            if line_idx >= len(self.lines):
                break
            if line_idx == self.focus_row:
                color = self.focus_color
            else:
                color = self.normal_color
            self.screen.addstr(row, 0, self.lines[line_idx], color)
        self.screen.addstr(scr_rows - 1, 0,
               '# focus: %d/%d row' % (self.focus_row, scr_rows))

    def draw(self):
        while True:
            self.__draw()

            x = self.screen.getch()
            c = chr(x)
            if c == 'j':
                self.focus_row = min(self.focus_row + 1, len(self.lines) - 1)
            elif c == 'k':
                self.focus_row = max(self.focus_row - 1, 0)
            elif c == 'q':
                break
            else:
                if self.input_handler is None:
                    continue
                rc = self.input_handler(self, c)
                if rc != 0:
                    break

def focused_mail(lines, focus_row):
    for idx in range(focus_row, 0, -1):
        line = lines[idx]
        if not line.startswith('['):
            continue
        mail_idx = int(line.split()[0][1:-1])
        return hkml_list.get_mail(mail_idx)

def mail_list_input_handler(slist, c):
    if c in ['o', '\n']:
        mail = focused_mail(slist.lines, slist.focus_row)
        lines = hkml_open.mail_display_str(mail, 80).split('\n')
        ScrollableList(slist.screen, lines, 0, slist.focus_color,
                       slist.normal_color, None).draw()
    return 0

def __view(stdscr):
    focus_row = 0
    text_lines = text_to_show.split('\n')

    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    focus_color = curses.color_pair(1)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    normal_color = curses.color_pair(2)

    ScrollableList(stdscr, text_lines, focus_row, focus_color, normal_color,
                   mail_list_input_handler).draw()

def view(text):
    global text_to_show
    text_to_show = text
    curses.wrapper(__view)
