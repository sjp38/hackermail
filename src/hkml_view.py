#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import curses
import os
import subprocess
import tempfile
import time

import hkml_cache
import hkml_export
import hkml_forward
import hkml_list
import hkml_open
import hkml_patch
import hkml_reply
import hkml_tag
import hkml_thread
import hkml_view_mails
import hkml_view_text
import hkml_write

'''
Curses-based TUI viewer for hkml list output.
'''

# ScrollableList

focus_color = None
normal_color = None
highlight_color = None

class InputHandler:
    to_handle = None
    handler_fn = None   # receives input_chr and an argument (ScrollableList)
    help_msg = None

    def __init__(self, to_handle, handler_fn, help_msg):
        self.to_handle = to_handle
        self.handler_fn = handler_fn
        self.help_msg = help_msg

    def handle(self, input_chr, arg):
        if not input_chr in self.to_handle:
            return
        return self.handler_fn(input_chr, arg)

class ScrollableList:
    screen = None
    lines = None
    focus_row = None
    input_handlers = None
    mail_idx_key_map = None
    highlight_keyword = None
    last_drawn = None
    menu_item_handlers = None
    scroll_cols = None
    longest_line_len = None

    def __init__(self, screen, lines, input_handlers):
        self.screen = screen
        self.lines = lines

        # set focus on middle of the screen or the content
        scr_rows, _ = screen.getmaxyx()
        self.focus_row = int(min(scr_rows / 2, len(lines) / 2))
        self.input_handlers = input_handlers
        self.scroll_cols = 0
        self.longest_line_len = sorted([len(line) for line in lines])[-1]

    def __draw(self):
        self.last_drawn = []
        self.screen.erase()
        scr_rows, scr_cols = self.screen.getmaxyx()
        start_row = max(int(self.focus_row - scr_rows / 2), 0)
        start_row = min(start_row, len(self.lines) - scr_rows + 1)
        start_row = max(start_row, 0)

        if 10 < scr_cols and scr_cols < 30:
            self.screen.addstr(0, 0, 'too narrow')
            return
        if scr_cols < 10:
            self.screen.addstr(0, 0, 'X')
            return

        for row in range(scr_rows - 1):
            line_idx = start_row + row
            if line_idx >= len(self.lines):
                break
            if line_idx == self.focus_row:
                color = focus_color
            else:
                color = normal_color

            line = self.lines[line_idx][
                    self.scroll_cols:self.scroll_cols + scr_cols]
            self.screen.addstr(row, 0, line, color)

            keyword = self.highlight_keyword
            if keyword is not None and keyword in line:
                search_from = 0
                while True:
                    idx = line[search_from:].find(keyword)
                    if idx == -1:
                        break
                    self.screen.addstr(row, search_from + idx, keyword,
                                       highlight_color)
                    search_from += len(keyword)

            self.last_drawn.append(self.lines[line_idx])
        if len(self.lines) < scr_rows - 1:
            self.last_drawn += [''] * (scr_rows - 1  - len(self.lines))

        orig_line = self.lines[self.focus_row]
        self.screen.addstr(scr_rows - 1, 0,
               '# focus: %d/%d row, %d/%d cols' % (
                   self.focus_row, len(self.lines), self.scroll_cols,
                   len(orig_line)))
        help_msg = 'Press ? for help'
        self.screen.addstr(scr_rows - 1, scr_cols - len(help_msg) - 1,
                           help_msg)

    def draw(self):
        while True:
            self.__draw()

            x = self.screen.getch()
            c = chr(x)
            break_loop = False
            for input_handler in self.input_handlers:
                err = input_handler.handle(c, self)
                if err:
                    break_loop = True
                    break
            if break_loop:
                break
            if self.mail_idx_key_map:
                _, last_mail_idx_key_map = hkml_list.get_last_mails_list()
                if self.mail_idx_key_map != last_mail_idx_key_map:
                    hkml_list.cache_list_str(
                            'thread_output', '\n'.join(self.lines),
                            self.mail_idx_key_map)

    def toast(self, message):
        scr_rows, scr_cols = self.screen.getmaxyx()
        self.screen.addstr(scr_rows - 1, 0, '# %s' % message)
        self.screen.refresh()
        time.sleep(1)

    def help_msg_lines(self):
        lines = []
        for handler in self.input_handlers:
            input_chrs = ','.join(handler.to_handle)
            input_chrs = input_chrs.replace('\n', '<Enter>')
            lines.append('%s: %s' % (input_chrs, handler.help_msg))
        return lines

    def set_menu_item_handlers(self, parent_list, item_handlers):
        self.input_handlers = get_menu_input_handlers()
        self.parent_list = parent_list
        self.menu_item_handlers = item_handlers
        for txt, _ in item_handlers:
            self.lines.append(txt)

def shell_mode_start(slist):
    slist.screen.clear()
    slist.screen.refresh()
    curses.reset_shell_mode()

def shell_mode_end(slist):
    curses.reset_prog_mode()
    slist.screen.clear()

def focus_down(c, slist):
    slist.focus_row = min(slist.focus_row + 1, len(slist.lines) - 1)

def focus_down_half_page(c, slist):
    rows, _ = slist.screen.getmaxyx()
    slist.focus_row = min(
            slist.focus_row + int(rows / 2), len(slist.lines) - 1)

def focus_up(c, slist):
    slist.focus_row = max(slist.focus_row - 1, 0)

def focus_up_half_page(c, slist):
    rows, _ = slist.screen.getmaxyx()
    slist.focus_row = max(slist.focus_row - int(rows / 2), 0)

def focus_set(c, slist):
    shell_mode_start(slist)

    answer = input('Enter line to move: ')
    if answer == 'start':
        answer = 0
    elif answer == 'end':
        answer = len(slist.lines) - 1
    else:
        try:
            answer = min(int(answer), len(slist.lines) - 1)
        except Exception as e:
            print('wrong answer')
            time.sleep(1)
            shell_mode_end(slist)
            return
    slist.focus_row = answer
    shell_mode_end(slist)

def highlight_keyword(c, slist):
    shell_mode_start(slist)

    keyword = input('Enter keyword to highlight: ')
    slist.highlight_keyword = keyword

    shell_mode_end(slist)

def focus_next_keyword(c, slist):
    for idx, line in enumerate(slist.lines[slist.focus_row + 1:]):
        if slist.highlight_keyword in line:
            slist.focus_row += idx + 1
            return
    slist.toast('no more keyword found')

def focus_prev_keyword(c, slist):
    for idx in range(slist.focus_row - 1, 0, -1):
        if slist.highlight_keyword in slist.lines[idx]:
            slist.focus_row = idx
            return
    slist.toast('no prev keyword found')

def scroll_left(c, slist):
    slist.scroll_cols = max(slist.scroll_cols - 1, 0)

def scroll_right(c, slist):
    _, cols = slist.screen.getmaxyx()
    scroll_cols = min(slist.scroll_cols + 1, slist.longest_line_len - cols)
    slist.scroll_cols = max(scroll_cols, 0)

def quit_list(c, slist):
    return 'quit list'

def quit_hkml(c, slist):
    raise Exception('terminate hkml', slist)

def show_help_msg_list(c, slist):
    ScrollableList(slist.screen, slist.help_msg_lines(),
                   scrollable_list_default_handlers()).draw()

def scrollable_list_default_handlers():
    return [
            InputHandler(['j'], focus_down, 'focus down'),
            InputHandler(['J'], focus_down_half_page, 'focus down half page'),
            InputHandler(['k'], focus_up, 'focus up'),
            InputHandler(['K'], focus_up_half_page, 'focus up half page'),
            InputHandler([':'], focus_set, 'focus specific line'),
            InputHandler(['/'], highlight_keyword, 'highlight keyword'),
            InputHandler(['n'], focus_next_keyword,
                         'focus the row of next highlighted keyword'),
            InputHandler(['N'], focus_prev_keyword,
                         'focus the row of prev highlighted keyword'),
            InputHandler(['h'], scroll_left, 'scroll left'),
            InputHandler(['l'], scroll_right, 'scroll right'),
            InputHandler(['q'], quit_list, 'quit current screen'),
            InputHandler(['Q'], quit_hkml, 'quit hkml'),
            InputHandler(['?'], show_help_msg_list, 'show help message'),
            ]

def execute_focused_item(c, slist):
    if slist.menu_item_handlers is None:
        return
    focused_line = slist.lines[slist.focus_row]
    for txt, fn in slist.menu_item_handlers:
        if txt == focused_line:
            fn(c, slist)

def get_menu_input_handlers():
    return scrollable_list_default_handlers() + [
            InputHandler(['\n'], execute_focused_item, 'execute focused item'),
            ]

def receive_file_path(for_read):
    while True:
        print('Enter the path to the file.')
        print()
        print('You can also enter')
        print('1. A directory (e.g., \'./\') to list files under it')
        print('2. \'cancel_input\' to cancelling this')
        print()
        answer = input('Enter: ')
        print()

        if answer == 'cancel_input':
            return None
        if os.path.isdir(answer):
                subprocess.call(['ls', '-al', answer])
                print()
                continue
        if for_read and not os.path.isfile(answer):
            print('\'%s\' is neither dir nor file.' % answer)
            print()
            continue
        return answer

def save_as(content):
    print('Save the content to')
    print('1. text file')
    print('2. clipboard')
    print()
    answer = input('Enter selection: ')
    try:
        answer = int(answer)
    except:
        print('wrong input')
        time.sleep(1)
        return
    if answer == 1:
        file_path = receive_file_path(for_read=False)
        if file_path is None:
            return
        with open(file_path, 'w') as f:
            f.write(content)
    elif answer == 2:
        _, tmp_path = tempfile.mkstemp(prefix='hkml_view_save_')
        with open(tmp_path, 'w') as f:
            f.write(content)
        rc = subprocess.call(['xclip', '-i', tmp_path, '-sel', 'clipboard'])
        os.remove(tmp_path)
        if rc != 0:
            print('saving in clipboard failed')
            time.sleep(1)

def handle_save_content_menu_selection(c, slist):
    shell_mode_start(slist)
    save_as('\n'.join(slist.parent_list.lines))
    shell_mode_end(slist)

save_parent_content_menu_item_handler = [
        '- save parent screen content as ...',
        handle_save_content_menu_selection]

def __view(stdscr, text_to_show, mail_idx_key_map):
    global focus_color
    global normal_color
    global highlight_color

    text_lines = text_to_show.split('\n')

    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    focus_color = curses.color_pair(1)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    normal_color = curses.color_pair(2)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    highlight_color = curses.color_pair(3)

    if mail_idx_key_map is not None:
        return hkml_view_mails.show_mails_list(
                stdscr, text_lines, mail_idx_key_map)
    return hkml_view_text.show_text_viewer(stdscr, text_lines)

def view(text, mail_idx_key_map):
    try:
        slist = curses.wrapper(__view, text, mail_idx_key_map)
    except Exception as e:
        if len(e.args) == 2 and e.args[0] == 'terminate hkml':
            slist = e.args[1]
        else:
            raise e
    print('\n'.join(slist.last_drawn))
