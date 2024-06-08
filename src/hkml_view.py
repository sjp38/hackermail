#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import curses
import subprocess
import tempfile
import time

import _hkml
import hkml_cache
import hkml_list
import hkml_open
import hkml_reply
import hkml_send
import hkml_thread

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
init_mail_idx_key_map = None

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
    focus_color = None
    normal_color = None
    input_handlers = None

    def __init__(self, screen, lines, focus_color, normal_color,
                 input_handlers):
        self.screen = screen
        self.lines = lines

        # set focus on middle of the screen or the content
        scr_rows, _ = screen.getmaxyx()
        self.focus_row = int(min(scr_rows / 2, len(lines) / 2))

        self.focus_color = focus_color
        self.normal_color = normal_color
        self.input_handlers = input_handlers

    def __draw(self):
        self.screen.erase()
        scr_rows, scr_cols = self.screen.getmaxyx()
        start_row = max(int(self.focus_row - scr_rows / 2), 0)
        start_row = min(start_row, len(self.lines) - scr_rows + 1)
        start_row = max(start_row, 0)

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
               '# focus: %d/%d row' % (self.focus_row, len(self.lines)))
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

def focus_down(c, slist):
    slist.focus_row = min(slist.focus_row + 1, len(slist.lines) - 1)

def focus_up(c, slist):
    slist.focus_row = max(slist.focus_row - 1, 0)

def quit_list(c, slist):
    return 'quit list'

def show_help_msg_list(c, slist):
    ScrollableList(slist.screen, slist.help_msg_lines(), slist.focus_color,
                   slist.normal_color,
                   scrollable_list_default_handlers()).draw()

def scrollable_list_default_handlers():
    return [
            InputHandler(['j'], focus_down, 'focus down'),
            InputHandler(['k'], focus_up, 'focus up'),
            InputHandler(['q'], quit_list, 'quit'),
            InputHandler(['?'], show_help_msg_list, 'show help message'),
            ]

def focused_mail_idx(lines, focus_row):
    for idx in range(focus_row, 0, -1):
        line = lines[idx]
        if not line.startswith('['):
            continue
        return int(line.split()[0][1:-1])
    return None

def get_focused_mail(slist):
    mail_idx = focused_mail_idx(slist.lines, slist.focus_row)
    if mail_idx is None:
        slist.toast('no mail focused?')
        return None
    mail_idx = '%d' % mail_idx
    if not mail_idx in slist.mail_idx_key_map:
        slist.toast('wrong index?')
        return None
    mail_key = slist.mail_idx_key_map[mail_idx]
    mail = hkml_cache.get_mail(key=mail_key)
    if mail is None:
        slist.toast('mail not cached?')
        return None
    return mail

def action_item_handler(c, slist):
    words = slist.lines[slist.focus_row].split()
    if words[:1] == ['git']:
        try:
            output = _hkml.cmd_lines_output(words)
        except Exception as e:
            output = ['failed: %s' % e]
        ScrollableList(slist.screen, output, slist.focus_color,
                       slist.normal_color,
                       scrollable_list_default_handlers()).draw()
    elif words[:1] == ['hkml']:
        slist.toast('not supported yet')

def is_git_hash(word):
    if len(word) < 10:
        return False
    for c in word:
        if c not in '0123456789abcdef':
            return False
    return True

def get_msgid_from_public_inbox_link(word):
    site_url = _hkml.get_manifest()['site']
    if not word.startswith(site_url) or len(word) < len(site_url) + 1:
        return None
    tokens = word.split('/')
    if tokens[-1] == '':
        return tokens[-2]
    return tokens[-1]

def find_actionable_items(slist):
    line = slist.lines[slist.focus_row]

    action_items = []
    for separator in [',', '(', ')', '/', '[', ']', '"']:
        line = line.replace(separator, ' ')
    for word in line.split():
        if is_git_hash(word):
            action_items.append('git log -n 5 %s' % word)
            action_items.append('git show %s' % word)

    line = slist.lines[slist.focus_row]
    for separator in [',', '(', ')', '[', ']', '"']:
        line = line.replace(separator, ' ')
    for word in line.split():
        msgid = get_msgid_from_public_inbox_link(word)
        if msgid is not None:
            action_items.append('hkml thread %s' % msgid)
            action_items.append('hkml open %s' % msgid)
    return action_items

def get_action_item_handlers():
    return scrollable_list_default_handlers() + [
            InputHandler(['\n'], action_item_handler,
                         'execute and show the ouptut')]

def show_available_action_items_handler(c, slist):
    items = find_actionable_items(slist)
    if len(items) == 0:
        slist.toast('no action item found')
        return
    ScrollableList(slist.screen, items, slist.focus_color, slist.normal_color,
                   get_action_item_handlers()).draw()

def get_mail_viewer_handlers():
    return scrollable_list_default_handlers() + [
            InputHandler(['\n'], show_available_action_items_handler,
                         'show available action items')
                ]

def open_mail_handler(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return

    lines = hkml_open.mail_display_str(mail, 80).split('\n')
    ScrollableList(slist.screen, lines, slist.focus_color,
                   slist.normal_color, get_mail_viewer_handlers()).draw()

def reply_mail_handler(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return

    curses.reset_shell_mode()
    hkml_reply.reply(mail, attach_files=None, format_only=None)
    curses.reset_prog_mode()
    slist.screen.clear()

def get_thread_input_handlers():
    return scrollable_list_default_handlers() + [
            InputHandler(['o', '\n'], open_mail_handler, 'open focused mail'),
            InputHandler(['r'], reply_mail_handler, 'reply focused mail'),
            ]

def list_thread_handler(c, slist):
    thread_txt, mail_idx_key_map = hkml_thread.thread_str(
            '%d' % focused_mail_idx(slist.lines, slist.focus_row),
            False, False)
    thread_list = ScrollableList(slist.screen, thread_txt.split('\n'),
            slist.focus_color, slist.normal_color, get_thread_input_handlers())
    thread_list.mail_idx_key_map = mail_idx_key_map
    thread_list.draw()

def get_mail_list_input_handlers():
    return get_thread_input_handlers() + [
            InputHandler(['t'], list_thread_handler, 'list complete thread'),
            ]

def __view(stdscr):
    text_lines = text_to_show.split('\n')

    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    focus_color = curses.color_pair(1)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    normal_color = curses.color_pair(2)

    slist = ScrollableList(stdscr, text_lines, focus_color, normal_color,
                           get_mail_list_input_handlers())
    slist.mail_idx_key_map = init_mail_idx_key_map
    slist.draw()

def view(text, mail_idx_key_map):
    global text_to_show
    global init_mail_idx_key_map
    text_to_show = text
    init_mail_idx_key_map = mail_idx_key_map
    curses.wrapper(__view)
