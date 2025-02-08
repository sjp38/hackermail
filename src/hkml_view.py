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

'''
object for CliQuestion.ask_selection()
'text' is displayed to the user with the selection question.
'handle_fn' of user-selected one is called if it is not None.  The function
    receives user-set CliQuestion.data, user-entered input (number), and the
    selected CliSelection object.
'data' can save any selection-specific data.
'''
class CliSelection:
    text = None
    handle_fn = None    # function receiving question data, answer, selection
    data = None         # for carrying selection-specific data

    def __init__(self, text, handle_fn=None, data=None):
        self.text = text
        self.handle_fn = handle_fn
        self.data = data

'''
For letting user show the output before showing others, e.g., returning to
previous ScrollableList screen.
'''
def cli_any_input(prompt):
    print('%s\n\nPress enter to return' % prompt)
    sys.stdin.read(1)

'''
question that will be provided to the user, in shell mode.
ask_input() and ask_selection() are the methods that user will really use.
'''
class CliQuestion:
    description = None
    prompt = None

    def __init__(self, prompt=None, desc=None):
        self.description = desc
        self.prompt = prompt

    '''
    internal method.  Shouldn't be called directly from CliQuestion user.
    '''
    def ask(self, data, selections, handle_fn, notify_completion):
        # return answer, selection, and error
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
            return None, None, 'canceled'

        selection = None
        selection_handle_fn = None
        if selections is not None:
            try:
                selection = selections[int(answer) - 1]
                selection_handle_fn = selection.handle_fn
            except:
                cli_any_input('Wrong input.')
                return None, None, 'wrong input'

        if selection_handle_fn is not None:
            err = selection_handle_fn(data, answer, selection)
        elif handle_fn is not None:
            err = handle_fn(data, answer)
            if err:
                # handle_fn() must notified the error.  Do not cli_any_input()
                return None, None, 'handler return err (%s)' % err

        if notify_completion:
            cli_any_input('Done.')
        return answer, selection, None

    '''
    Ask user to answer any text input.  If handle_fn is not None, the function
    is called with 'data' and user's input to the question.

    Should be invoked in shell mode (show shell_mode_start() and
    shell_mode_end()).

    Returns user's input to the question and error.
    '''
    def ask_input(self, data=None, handle_fn=None, notify_completion=False):
        answer, selection, err = self.ask(data, None, handle_fn,
                                          notify_completion)
        return answer, err

    '''
    Ask user to select on of CliSelection objects.  If the selected
    CliSelection has handle_fn field set, it is invoked.

    Should be invoked in shell mode (show shell_mode_start() and
    shell_mode_end()).

    Returns user's input to the question, selected CliSelection, and error.
    '''
    def ask_selection(self, selections, data=None, notify_completion=False):
        if self.prompt is None:
            self.prompt = 'Enter the item number'
        return self.ask(data, selections, None, notify_completion)

# ScrollableList

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

def tabs_to_spaces(line, spaces_per_tab):
    chrs = []
    idx = 0
    for chr in line:
        if chr != '\t':
            chrs.append(chr)
            idx += 1
            continue
        nr_spaces = (idx // spaces_per_tab + 1) * spaces_per_tab - idx
        chrs += [' '] * nr_spaces
        idx += nr_spaces
    return ''.join(chrs)

def wrap_line(line, cols):
    if len(line) < cols:
        return [line]
    if line[:2] in ['> ', '+ ', '- ']:
        prefix = line[:2]
        line = line[2:]
    else:
        prefix = ''
    last_space = None
    for idx, c in enumerate(line):
        if c.isspace():
            last_space = idx
        if idx >= cols and last_space is not None:
            break
    if last_space is None:
        last_space = len(line)
    wrapped_lines = ['%s%s' % (prefix, line[:last_space])]
    next_line = line[last_space + 1:]
    if len(next_line) > 0:
        next_line = '%s%s' % (prefix, next_line)
        wrapped_lines += wrap_line(next_line, cols)
    return wrapped_lines

def wrap_text(lines, cols):
    wrapped_lines = []
    for line in lines:
        wrapped_lines += wrap_line(line, cols)
    return wrapped_lines

class ScrollableList:
    screen = None
    lines = None
    unwrapped_lines = None
    focus_row = None
    focus_col = None
    input_handlers = None
    search_keyword = None
    searched_lines = None
    last_drawn = None
    longest_line_len = None
    after_input_handle_callback = None
    data = None
    parent_list = None
    display_effect_callback = None
    color_callback = None
    enable_highlight = None

    # constants for display_effect_callback return values
    effect_normal = curses.A_NORMAL
    effect_dim = curses.A_DIM
    effect_bold = curses.A_BOLD
    try:
        effect_italic = curses.A_ITALIC
    except:
        effect_italic = curses.A_BOLD
    effect_blink = curses.A_BLINK
    effect_reverse = curses.A_REVERSE
    effect_underline = curses.A_UNDERLINE

    def set_lines(self, lines):
        converted = []
        for line in lines:
            converted.append(tabs_to_spaces(line, 8))
        lines = converted
        self.lines = lines
        self.longest_line_len = sorted([len(line) for line in lines])[-1]
        if self.focus_col is not None:
            self.focus_col = min(self.focus_col, self.longest_line_len - 1)
        if self.focus_row is not None:
            self.focus_row = min(self.focus_row, len(lines) - 1)

    def __init__(self, screen, lines, input_handlers):
        self.screen = screen

        self.set_lines(lines)

        # set focus on middle of the screen or the content
        scr_rows, _ = screen.getmaxyx()
        self.focus_row = int(min(scr_rows / 2, len(lines) / 2))
        self.input_handlers = scrollable_list_default_handlers()
        if input_handlers:
            self.input_handlers += input_handlers
        handled_inputs = {}
        for input_handler in self.input_handlers:
            for c in input_handler.to_handle:
                if c in handled_inputs:
                    raise Exception('DUPLICATED INPUT HANDLER for %s' % c)
                handled_inputs[c] = True
        self.focus_col = 0
        self.search_keyword = '['
        self.searched_lines = []

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

        max_horizon_scroll_len = self.longest_line_len - scr_cols
        if max_horizon_scroll_len < 0:
            # no need to horizon-scroll at all
            draw_start_col = 0
        elif self.focus_col < max_horizon_scroll_len:
            draw_start_col = self.focus_col
        else:
            # don't scroll right if it will not show something more
            draw_start_col = max_horizon_scroll_len

        for row in range(scr_rows - 1):
            line_idx = start_row + row
            if line_idx >= len(self.lines):
                break

            line = self.lines[line_idx][
                    draw_start_col:draw_start_col + scr_cols]

            if self.color_callback:
                color = self.color_callback(self, line_idx)
            else:
                color = normal_color

            if self.display_effect_callback:
                color_attrib = self.display_effect_callback(self, line_idx)
            else:
                color_attrib = curses.A_NORMAL

            if line_idx in self.searched_lines and self.enable_highlight:
                self.screen.addstr(row, 0, line, highlight_color | color_attrib)
            else:
                self.screen.addstr(row, 0, line, color | color_attrib)

            keyword = self.search_keyword
            if self.enable_highlight and keyword is not None and \
                    keyword in line:
                search_from = 0
                while True:
                    idx = line[search_from:].find(keyword)
                    if idx == -1:
                        break
                    self.screen.addstr(row, search_from + idx, keyword,
                                       highlight_color | color_attrib)
                    search_from += len(keyword)


            self.last_drawn.append(self.lines[line_idx])
        if len(self.lines) < scr_rows - 1:
            self.last_drawn += [''] * (scr_rows - 1  - len(self.lines))

        orig_line = self.lines[self.focus_row]
        self.screen.addstr(scr_rows - 1, 0,
                           '# focus: %d/%d row, %d/%d cols' % (
                               self.focus_row, len(self.lines), self.focus_col,
                               self.longest_line_len - 1))
        help_msg = 'Press ? for help'
        self.screen.addstr(scr_rows - 1, scr_cols - len(help_msg) - 1,
                           help_msg)
        self.screen.move(self.focus_row - start_row,
                         self.focus_col - draw_start_col)

    def draw(self):
        while True:
            self.__draw()

            x = self.screen.getch()
            if x == curses.KEY_DOWN:
                c = 'key_down'
            elif x == curses.KEY_UP:
                c = 'key_up'
            elif x == curses.KEY_LEFT:
                c = 'key_left'
            elif x == curses.KEY_RIGHT:
                c = 'key_right'
            else:
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

    def wrap_text(self):
        _, scr_cols = self.screen.getmaxyx()
        self.unwrapped_lines = self.lines
        wrapped_lines = wrap_text(self.lines, scr_cols)
        self.set_lines(wrapped_lines)

    def unwrap_text(self):
        self.set_lines(self.unwrapped_lines)
        self.unwrapped_lines = None

    def wrapped_text(self):
        return self.unwrapped_lines is not None

    def set_searched_lines(self, line_idxs):
        self.searched_lines = line_idxs

def shell_mode_start(slist_or_screen):
    if type(slist_or_screen) == ScrollableList:
        screen = slist_or_screen.screen
    else:
        screen = slist_or_screen
    screen.clear()
    screen.refresh()
    curses.reset_shell_mode()

def shell_mode_end(slist_or_screen):
    if type(slist_or_screen) == ScrollableList:
        screen = slist_or_screen.screen
    else:
        screen = slist_or_screen
    curses.reset_prog_mode()
    screen.clear()

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

def search_keyword(c, slist):
    shell_mode_start(slist)

    prompt = '[Search keyword]\n\n' \
             "Current Keyword: '{}'\n"\
             'Searched keyword highlighting: {}\n' \
             .format(slist.search_keyword,
                     'Enabled' if slist.enable_highlight else 'Disabled')
    print(prompt)

    question = CliQuestion('Enter a new keyword to search')

    def handle_fn(slist, answer):
        slist.search_keyword = answer

    _, error = question.ask_input(slist, handle_fn=handle_fn)

    if error == 'canceled':
        shell_mode_end(slist)
        return

    question = 'Would you like to enable search highlighting? [Y/n] '
    answer = input(question)

    if answer == 'n':
        slist.enable_highlight = False
    else:
        slist.enable_highlight = True

    shell_mode_end(slist)

def focus_next_keyword(c, slist):
    for idx, line in enumerate(slist.lines[slist.focus_row + 1:]):
        idx = slist.focus_row + idx + 1
        if idx in slist.searched_lines or slist.search_keyword in line:
            slist.focus_row = idx
            return
    slist.toast('no more keyword found')

def focus_prev_keyword(c, slist):
    for idx in range(slist.focus_row - 1, 0, -1):
        if (idx in slist.searched_lines or
            slist.search_keyword in slist.lines[idx]):
            slist.focus_row = idx
            return
    slist.toast('no prev keyword found')

def focus_left(c, slist):
    slist.focus_col = max(slist.focus_col - 1, 0)

def focus_right(c, slist):
    _, cols = slist.screen.getmaxyx()
    focus_col = min(slist.focus_col + 1, slist.longest_line_len - 1)
    slist.focus_col = max(focus_col, 0)

def quit_list(c, slist):
    return 'quit list'

def quit_hkml(c, slist):
    raise Exception('terminate hkml', slist)

def show_help_msg_list(c, slist):
    ScrollableList(slist.screen, slist.help_msg_lines(), None).draw()

def scrollable_list_default_handlers():
    return [
            InputHandler(['j', 'key_down'], focus_down, 'focus down'),
            InputHandler(['J'], focus_down_half_page, 'focus down half page'),
            InputHandler(['k', 'key_up'], focus_up, 'focus up'),
            InputHandler(['K'], focus_up_half_page, 'focus up half page'),
            InputHandler([':'], focus_set, 'focus specific line'),
            InputHandler(['/'], search_keyword, 'search keyword'),
            InputHandler(['n'], focus_next_keyword,
                         'focus the row of next searched keyword'),
            InputHandler(['N'], focus_prev_keyword,
                         'focus the row of prev searched keyword'),
            InputHandler(['h', 'key_left'], focus_left, 'focus left'),
            InputHandler(['l', 'key_right'], focus_right, 'focus right'),
            InputHandler(['q'], quit_list, 'quit current screen'),
            InputHandler(['Q'], quit_hkml, 'quit hkml'),
            InputHandler(['?'], show_help_msg_list, 'show help message'),
            ]

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
        _, err = q.ask_input([answers, for_read], handle_fn)
        if err == 'canceled':
            return None
        if len(answers) != 1:
            continue
        return answers[0]

def save_as(content):
    q = CliQuestion(desc='Save the content to', prompt='Enter selection')
    def txt_handle_fn(data, answer, selection):
        content = data
        file_path = receive_file_path(for_read=False)
        if file_path is None:
            return
        with open(file_path, 'w') as f:
            f.write(content)

    def clipboard_handle_fn(data, answer, selection):
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

def __view(stdscr, text_to_show, data, view_type):
    global focus_color
    global normal_color
    global highlight_color

    global add_color
    global delete_color
    global original_color

    curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    focus_color = curses.color_pair(1)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    normal_color = curses.color_pair(2)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    highlight_color = curses.color_pair(3)

    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
    add_color = curses.color_pair(4)
    curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
    delete_color = curses.color_pair(5)

    if curses.can_change_color():
        # Curses RGB are in [0,1000], not [0,255]
        curses.init_color(10, 700, 700, 1000)
        curses.init_pair(6, 10, curses.COLOR_BLACK)
    else:
        curses.init_pair(6, curses.COLOR_BLUE, curses.COLOR_BLACK)
    original_color = curses.color_pair(6)

    if view_type in ['mail', 'text']:
        return hkml_view_text.show_text_viewer(
                stdscr, text_to_show.split('\n'))
    elif view_type == 'gen_mails_list':
        return hkml_view_mails.gen_show_mails_list(
                stdscr, data)
    else:
        raise Exception('unknonw view : %s' % view_type)

def view(text, data, view_type):
    try:
        slist = curses.wrapper(__view, text, data, view_type)
    except Exception as e:
        if len(e.args) == 2 and e.args[0] == 'terminate hkml':
            slist = e.args[1]
        else:
            raise e
    # the view was well finished.
    if slist is not None:
        print('\n'.join(slist.last_drawn))

def gen_view_mails_list(list_args):
    view('', list_args, 'gen_mails_list')

def view_mail(text, mail):
    view(text, mail, 'mail')

def view_text(text):
    view(text, None, 'text')
