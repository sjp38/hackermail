#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import curses
import os
import subprocess
import sys
import tempfile
import time

import _hkml
import hkml_list
import hkml_view_mails
import hkml_view_text

'''
Curses-based TUI viewer for hkml list/open outputs.
'''

# CLI menu

class CliSelection:
    text = None
    handle_fn = None    # function receiving data and the answer

    def __init__(self, text, handle_fn):
        self.text = text
        self.handle_fn = handle_fn

def cli_any_input(prompt):
    print('%s  Press any key to return' % prompt)
    sys.stdin.read(1)

class CliQuestion:
    description = None
    prompt = None

    def __init__(self, prompt=None, desc=None):
        self.description = desc
        self.prompt = prompt

    def ask(self, data, selections, handle_fn, notify_completion):
        lines = []
        if self.description is not None:
            lines.append(self.description)
            lines.append('')
        if selections is not None:
            for idx, selection in enumerate(selections):
                lines.append('%d: %s' % (idx + 1, selection.text))
            lines.append('')
        if len(lines) > 0:
            print('\n'.join(lines))

        answer = input('%s (enter \'\' to cancel): ' % self.prompt)
        if answer == '':
            cli_any_input('Canceled.')
            return 'canceled'

        if selections is not None:
            try:
                handle_fn = selections[int(answer) - 1].handle_fn
            except:
                cli_any_input('Wrong input.')
                return 'wrong input'

        err = handle_fn(data, answer)
        if err:
            # handle_fn() must notified the error.
            return

        if notify_completion:
            cli_any_input('Done.')

    def ask_input(self, data, handle_fn, notify_completion=False):
        return self.ask(data, None, handle_fn, notify_completion)

    def ask_selection(self, data, selections, notify_completion=False):
        if self.prompt is None:
            self.prompt = 'Enter the item number'
        return self.ask(data, selections, None, notify_completion)

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
    highlight_keyword = None
    last_drawn = None
    menu_item_handlers = None
    scroll_cols = None
    longest_line_len = None
    after_input_handle_callback = None
    data = None
    parent_list = None

    def __init__(self, screen, lines, input_handlers):
        self.screen = screen
        self.lines = lines

        # set focus on middle of the screen or the content
        scr_rows, _ = screen.getmaxyx()
        self.focus_row = int(min(scr_rows / 2, len(lines) / 2))
        self.input_handlers = scrollable_list_default_handlers()
        if input_handlers:
            self.input_handlers += input_handlers
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
            if self.after_input_handle_callback is not None:
                self.after_input_handle_callback(self)

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
        self.input_handlers += [
                InputHandler(
                    ['\n'], execute_focused_item, 'execute focused item'),
                ]

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

    question = CliQuestion(
            desc='\n'.join([
                'Move focus to arbitrary line', '',
                'point line by \'start\', \'end\', or the line number']),
            prompt='Enter line to focus')

    def handle_fn(data, answer):
        slist = data
        if answer == 'start':
            answer = 0
        elif answer == 'end':
            answer = len(slist.lines) - 1
        else:
            try:
                answer = min(int(answer), len(slist.lines) - 1)
            except Exception as e:
                cli_any_input('wrong answer')
                return 'wrong answer'
        slist.focus_row = answer
        return None

    question.ask_input(slist, handle_fn=handle_fn)
    shell_mode_end(slist)

def highlight_keyword(c, slist):
    shell_mode_start(slist)

    question = CliQuestion('Enter keyword to highlight')

    def handle_fn(slist, answer):
        slist.highlight_keyword = answer

    question.ask_input(slist, handle_fn=handle_fn)
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
    ScrollableList(slist.screen, slist.help_msg_lines(), None).draw()

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

def receive_file_path(for_read):
    answers = []
    def handle_fn(data, answer):
        answers, for_read = data
        if os.path.isdir(answer):
                subprocess.call(['ls', '-al', answer])
                print()
                return
        if for_read and not os.path.isfile(answer):
            print('\'%s\' is neither dir nor file.' % answer)
            print()
            return 'wrong input'
        answers.append(answer)

    while True:
        q = CliQuestion(
                desc='\n'.join([
                    'Enter ',
                    '1. the path to the file, or',
                    '2. a directory (e.g., "./") to list files under it.',
                    ]),
                prompt='')
        err = q.ask_input([answers, for_read], handle_fn)
        if err == 'canceled':
            return None
        if len(answers) != 1:
            continue
        return answers[0]

def save_as(content):
    q = CliQuestion(desc='Save the content to', prompt='Enter selection')
    def txt_handle_fn(data, answer):
        content = data
        file_path = receive_file_path(for_read=False)
        if file_path is None:
            return
        with open(file_path, 'w') as f:
            f.write(content)

    def clipboard_handle_fn(data, answer):
        content = data
        _, tmp_path = tempfile.mkstemp(prefix='hkml_view_save_')
        with open(tmp_path, 'w') as f:
            f.write(content)
        rc = subprocess.call(['xclip', '-i', tmp_path, '-sel', 'clipboard'])
        os.remove(tmp_path)
        if rc != 0:
            return 'saving in clipboard failed'

    q.ask_selection(
            data=content, selections=[
                CliSelection('text file', txt_handle_fn),
                CliSelection('clipboard', clipboard_handle_fn)])

def handle_save_content_menu_selection(c, slist):
    shell_mode_start(slist)
    save_as('\n'.join(slist.parent_list.lines))
    shell_mode_end(slist)

save_parent_content_menu_item_handler = [
        '- save parent screen content as ...',
        handle_save_content_menu_selection]

def __view(stdscr, text_to_show, data):
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

    if data is None or type(data) == _hkml.Mail:
        return hkml_view_text.show_text_viewer(stdscr, text_lines)
    # data would be mail_idx_key_map
    return hkml_view_mails.show_mails_list(stdscr, text_lines, data)

def view(text, data):
    try:
        slist = curses.wrapper(__view, text, data)
    except Exception as e:
        if len(e.args) == 2 and e.args[0] == 'terminate hkml':
            slist = e.args[1]
        else:
            raise e
    print('\n'.join(slist.last_drawn))
