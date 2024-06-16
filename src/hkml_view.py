#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import curses
import subprocess
import tempfile
import time

import _hkml
import hkml_cache
import hkml_forward
import hkml_list
import hkml_open
import hkml_reply
import hkml_send
import hkml_tag
import hkml_thread
import hkml_write

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

    def __init__(self, screen, lines, input_handlers):
        self.screen = screen
        self.lines = lines

        # set focus on middle of the screen or the content
        scr_rows, _ = screen.getmaxyx()
        self.focus_row = int(min(scr_rows / 2, len(lines) / 2))
        self.input_handlers = input_handlers

    def __draw(self):
        drawn = []
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
                color = focus_color
            else:
                color = normal_color

            line = self.lines[line_idx]
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

            drawn.append(self.lines[line_idx])
        if len(self.lines) < scr_rows - 1:
            drawn += [''] * (scr_rows - 1  - len(self.lines))
        self.screen.addstr(scr_rows - 1, 0,
               '# focus: %d/%d row' % (self.focus_row, len(self.lines)))
        help_msg = 'Press ? for help'
        self.screen.addstr(scr_rows - 1, scr_cols - len(help_msg) - 1,
                           help_msg)
        return drawn

    def draw(self):
        while True:
            last_drawn = self.__draw()

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
                _, last_mail_idx_key_map = hkml_list.get_last_list()
                if self.mail_idx_key_map != last_mail_idx_key_map:
                    hkml_list.cache_list_str(
                            'thread_output', '\n'.join(self.lines),
                            self.mail_idx_key_map)
        return last_drawn

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

def shell_mode_start():
    slist.screen.clear()
    slist.screen.refresh()
    curses.reset_shell_mode()

def shell_mode_end(slist):
    curses.reset_prog_mode()
    slist.screen.clear()

def focus_down(c, slist):
    slist.focus_row = min(slist.focus_row + 1, len(slist.lines) - 1)

def focus_up(c, slist):
    slist.focus_row = max(slist.focus_row - 1, 0)

def highlight_keyword(c, slist):
    slist.screen.clear()
    slist.screen.refresh()
    curses.reset_shell_mode()

    keyword = input('Enter keyword to highlight: ')
    slist.highlight_keyword = keyword

    curses.reset_prog_mode()
    slist.screen.clear()

def quit_list(c, slist):
    return 'quit list'

def show_help_msg_list(c, slist):
    ScrollableList(slist.screen, slist.help_msg_lines(),
                   scrollable_list_default_handlers()).draw()

def scrollable_list_default_handlers():
    return [
            InputHandler(['j'], focus_down, 'focus down'),
            InputHandler(['k'], focus_up, 'focus up'),
            InputHandler(['/'], highlight_keyword, 'highlight keyword'),
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
    if len(words) < 2:
        return
    if words[0] != '-':
        return
    words = words[1:]
    if words[:1] == ['git']:
        try:
            output = _hkml.cmd_lines_output(words)
        except Exception as e:
            output = ['failed: %s' % e]
        ScrollableList(slist.screen, output, get_text_viewer_handlers()).draw()
    elif words[:1] == ['hkml']:
        msgid = '<%s>' % words[-1]
        thread_txt, mail_idx_key_map = hkml_thread.thread_str(msgid,
                False, False)
        hkml_cache.writeback_mails()
        hkml_list.cache_list_str('thread_output', thread_txt, mail_idx_key_map)
        if words[1] == 'thread':
            thread_list = ScrollableList(
                    slist.screen, thread_txt.split('\n'),
                    get_mails_list_input_handlers())
            thread_list.mail_idx_key_map = mail_idx_key_map
            thread_list.draw()
        elif words[1] == 'open':
            for idx, cache_key in mail_idx_key_map.items():
                mail = hkml_cache.get_mail(key=cache_key)
                if mail is None:
                    continue
                if mail.get_field('message-id') == msgid:
                    _, cols = slist.screen.getmaxyx()
                    lines = hkml_open.mail_display_str(mail, cols).split('\n')
                    ScrollableList(slist.screen, lines,
                                   get_text_viewer_handlers()).draw()
                    break
        else:
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
            action_items.append('- git show %s' % word)
            action_items.append('- git log -n 5 %s' % word)
            action_items.append('- git log --oneline -n 64 %s' % word)

    line = slist.lines[slist.focus_row]
    for separator in [',', '(', ')', '[', ']', '"']:
        line = line.replace(separator, ' ')
    for word in line.split():
        msgid = get_msgid_from_public_inbox_link(word)
        if msgid is not None:
            action_items.append('- hkml thread %s' % msgid)
            action_items.append('- hkml open %s' % msgid)
    return action_items

def get_action_item_handlers():
    return scrollable_list_default_handlers() + [
            InputHandler(['\n'], action_item_handler,
                         'execute focused item')]

def show_available_action_items_handler(c, slist):
    items = find_actionable_items(slist)
    if len(items) == 0:
        slist.toast('no action item found')
        return
    items = ['selected line: %s' % slist.lines[slist.focus_row], '',
             'focus an item below and press Enter', ''] + items
    ScrollableList(slist.screen, items, get_action_item_handlers()).draw()

def get_text_viewer_handlers():
    return scrollable_list_default_handlers() + [
            InputHandler(['m', '\n'], show_available_action_items_handler,
                         'open menu')
                ]

def open_mail_handler(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return

    _, cols = slist.screen.getmaxyx()
    lines = hkml_open.mail_display_str(mail, cols).split('\n')
    ScrollableList(slist.screen, lines, get_text_viewer_handlers()).draw()

def reply_mail_handler(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return

    curses.reset_shell_mode()
    hkml_reply.reply(mail, attach_files=None, format_only=None)
    curses.reset_prog_mode()
    slist.screen.clear()

def mails_list_open_mail(c, slist):
    open_mail_handler(c, slist.parent_list)

def mails_list_reply(c, slist):
    reply_mail_handler(c, slist.parent_list)

def mails_list_list_thread(c, slist):
    list_thread_handler(c, slist.parent_list)

def mails_list_forward(c, slist):
    mail = get_focused_mail(slist.parent_list)
    if mail is None:
        return
    curses.reset_shell_mode()
    hkml_forward.forward(mail)
    curses.reset_prog_mode()
    slist.screen.clear()

def mails_list_continue_draft(c, slist):
    mail = get_focused_mail(slist.parent_list)
    if mail is None:
        return
    curses.reset_shell_mode()
    hkml_write.write_send_mail(
            draft_mail=mail, subject=None, in_reply_to=None, to=None,
            cc=None, body=None, attach=None, format_only=None)
    curses.reset_prog_mode()
    slist.screen.clear()

def mails_list_show_tags(c, slist):
    mail = get_focused_mail(slist.parent_list)
    if mail is None:
        return
    msgid = mail.get_field('message-id')
    tags_map = hkml_tag.read_tags_file()
    if not msgid in tags_map:
        slist.toast('the mail has no tag')
        return
    tags = tags_map[msgid]['tags']

    slist.screen.clear()
    slist.screen.refresh()
    curses.reset_shell_mode()

    print('the mail has below tags:')
    for tag in tags:
        print('- %s' % tag)
    print()
    _ = input('Press <Enter> to return')
    curses.reset_prog_mode()
    slist.screen.clear()

def mails_list_add_tags(c, slist):
    mail = get_focused_mail(slist.parent_list)
    if mail is None:
        return
    slist.screen.clear()
    slist.screen.refresh()
    curses.reset_shell_mode()

    msgid = mail.get_field('message-id')
    tags_map = hkml_tag.read_tags_file()
    current_tags = tags_map[msgid]['tags']
    if len(current_tags) > 0:
        print('the mail has below tags:')
        for tag in current_tags:
            print('- %s' % tag)
        print()

    prompt = ' '.join(['Enter tags separated by white spaces',
                       '(enter \'cancel_tag\' to cancel): '])
    tags = input(prompt).split()
    if not 'cancel_tag' in tags:
        hkml_tag.do_add_tags(mail, tags)
    curses.reset_prog_mode()
    slist.screen.clear()

def mails_list_remove_tags(c, slist):
        mail = get_focused_mail(slist.parent_list)
        if mail is None:
            return
        msgid = mail.get_field('message-id')
        tags_map = hkml_tag.read_tags_file()
        if not msgid in tags_map:
            slist.toast('the mail has no tag')
            return
        tags = tags_map[msgid]['tags']

        slist.screen.clear()
        slist.screen.refresh()
        curses.reset_shell_mode()

        print('the mail has below tags:')
        for tag in tags:
            print('- %s' % tag)
        print()
        while True:
            prompt = ' '.join(
                    ['Enter tags to remove separted by white space',
                     '(enter \'cancel_tag\' to cancel): '])
            tags_to_remove = input(prompt).split()
            if 'cancel_tag' in tags_to_remove:
                break
            for tag in tags_to_remove:
                if not tag in tags:
                    print('the mail is not tagged as %s' % tag)
                    continue
            break
        if not 'cancel_tag' in tags_to_remove:
            hkml_tag.do_remove_tags(mail, tags_to_remove)
        curses.reset_prog_mode()
        slist.screen.clear()

mails_list_menu = [
        ['- open', mails_list_open_mail],
        ['- reply', mails_list_reply],
        ['- list complete thread', mails_list_list_thread],
        ['- continue draft writing', mails_list_continue_draft],
        ['- show tags', mails_list_show_tags],
        ['- add tags', mails_list_add_tags],
        ['- remove tags', mails_list_remove_tags],
        ]

def mails_list_menu_selection_handler(c, slist):
    focused_line = slist.lines[slist.focus_row]
    for txt, fn in mails_list_menu:
        if txt == focused_line:
            fn(c, slist)

def get_menu_input_handlers():
    return scrollable_list_default_handlers() + [
            InputHandler(['\n'], mails_list_menu_selection_handler,
                         'execute focused item'),
            ]

def thread_menu_handler(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return
    menu_lines = [
            'selected mail: %s' % mail.subject,
            '',
            'focus an item below and press Enter',
            '']
    for txt, _ in mails_list_menu:
        menu_lines.append(txt)

    menu_list = ScrollableList(
            slist.screen, menu_lines, get_menu_input_handlers())
    menu_list.parent_list = slist
    menu_list.draw()

def get_mails_list_input_handlers():
    return scrollable_list_default_handlers() + [
            InputHandler(['o', '\n'], open_mail_handler, 'open focused mail'),
            InputHandler(['r'], reply_mail_handler, 'reply focused mail'),
            InputHandler(['t'], list_thread_handler, 'list complete thread'),
            InputHandler(['m'], thread_menu_handler, 'open menu'),
            ]

def list_thread_handler(c, slist):
    thread_txt, mail_idx_key_map = hkml_thread.thread_str(
            '%d' % focused_mail_idx(slist.lines, slist.focus_row),
            False, False)
    hkml_cache.writeback_mails()
    hkml_list.cache_list_str('thread_output', thread_txt, mail_idx_key_map)

    thread_list = ScrollableList(slist.screen, thread_txt.split('\n'),
                                 get_mails_list_input_handlers())
    thread_list.mail_idx_key_map = mail_idx_key_map
    thread_list.draw()

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
        slist = ScrollableList(stdscr, text_lines,
                               get_mails_list_input_handlers())
        slist.mail_idx_key_map = mail_idx_key_map
    else:
        slist = ScrollableList(stdscr, text_lines, get_text_viewer_handlers())
    return slist.draw()

def view(text, mail_idx_key_map):
    last_drawn = curses.wrapper(__view, text, mail_idx_key_map)
    print('\n'.join(last_drawn))
