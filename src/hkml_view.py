#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import curses
import os
import subprocess
import tempfile
import time

import _hkml
import hkml_cache
import hkml_export
import hkml_forward
import hkml_list
import hkml_open
import hkml_patch
import hkml_reply
import hkml_send
import hkml_tag
import hkml_thread
import hkml_write

'''
Curses-based TUI viewer for hkml list output.
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
    last_drawn = None
    menu_item_handlers = None

    def __init__(self, screen, lines, input_handlers):
        self.screen = screen
        self.lines = lines

        # set focus on middle of the screen or the content
        scr_rows, _ = screen.getmaxyx()
        self.focus_row = int(min(scr_rows / 2, len(lines) / 2))
        self.input_handlers = input_handlers

    def __draw(self):
        self.last_drawn = []
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

            self.last_drawn.append(self.lines[line_idx])
        if len(self.lines) < scr_rows - 1:
            self.last_drawn += [''] * (scr_rows - 1  - len(self.lines))
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

    def set_menu_item_handlers(self, item_handlers):
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
            InputHandler(['q'], quit_list, 'quit current screen'),
            InputHandler(['Q'], quit_hkml, 'quit hkml'),
            InputHandler(['?'], show_help_msg_list, 'show help message'),
            ]

def menu_selection_handler(c, slist):
    if slist.menu_item_handlers is None:
        return
    focused_line = slist.lines[slist.focus_row]
    for txt, fn in slist.menu_item_handlers:
        if txt == focused_line:
            fn(c, slist)

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

def text_viewer_menu_exec_git(c, slist):
    words = slist.lines[slist.focus_row].split()[1:]
    try:
        output = subprocess.check_output(
                words, stderr=subprocess.DEVNULL).decode().split('\n')
    except Exception as e:
        output = ['failed: %s' % e, '',
                  'wrong commit id, or you are not on the git repo?']
    ScrollableList(slist.screen, output, get_text_viewer_handlers()).draw()

def get_thread_txt_mail_idx_key_map(msgid):
    thread_txt, mail_idx_key_map = hkml_thread.thread_str(msgid,
            False, False)
    hkml_cache.writeback_mails()
    hkml_list.cache_list_str('thread_output', thread_txt, mail_idx_key_map)
    return thread_txt, mail_idx_key_map

def text_viewer_menu_hkml_thread(c, slist):
    msgid = '<%s>' % slist.lines[slist.focus_row].split()[1:][-1]
    thread_txt, mail_idx_key_map = get_thread_txt_mail_idx_key_map(msgid)
    thread_list = ScrollableList(
            slist.screen, thread_txt.split('\n'),
            get_mails_list_input_handlers())
    thread_list.mail_idx_key_map = mail_idx_key_map
    thread_list.draw()

def text_viewer_menu_hkml_open(c, slist):
    msgid = '<%s>' % slist.lines[slist.focus_row].split()[1:][-1]
    thread_txt, mail_idx_key_map = get_thread_txt_mail_idx_key_map(msgid)
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

def text_viewer_menu_save_content(c, slist):
    shell_mode_start(slist)
    save_as('\n'.join(slist.parent_list.lines))
    shell_mode_end(slist)

def action_item_handler(c, slist):
    words = slist.lines[slist.focus_row].split()
    if len(words) < 2:
        return
    if words[0] != '-':
        return
    words = words[1:]
    if words[:1] == ['git']:
        text_viewer_menu_exec_git(c, slist)
    elif words[:1] == ['hkml']:
        if words[1] == 'thread':
            text_viewer_menu_hkml_thread(c, slist)
        elif words[1] == 'open':
            text_viewer_menu_hkml_open(c, slist)
        else:
            slist.toast('not supported yet')
    elif words[:1] == ['save']:
        text_viewer_menu_save_content(c, slist)

def is_git_hash(word):
    if len(word) < 10:
        return False
    for c in word:
        if c not in '0123456789abcdef':
            return False
    return True

def get_msgid_from_public_inbox_link(word):
    '''
    If it is http url and has @ in a field, assume it is msgid link
    '''
    if not word.startswith('http'):
        return None
    tokens = word.split('/')
    if len(tokens) < 4:
        return None
    for token in tokens[3:]:
        if '@' in token:
            return token
    return None

def build_text_view_menu_item_handlers(slist):
    line = slist.lines[slist.focus_row]

    item_handlers = []
    for separator in [',', '(', ')', '/', '[', ']', '"']:
        line = line.replace(separator, ' ')
    for word in line.split():
        if is_git_hash(word):
            item_handlers.append(
                    ['- git show %s' % word, text_viewer_menu_exec_git])
            item_handlers.append(
                    ['- git log -n 5 %s' % word, text_viewer_menu_exec_git])
            item_handlers.append(
                    ['- git log --oneline -n 64 %s' % word,
                     text_viewer_menu_exec_git])

    line = slist.lines[slist.focus_row]
    for separator in [',', '(', ')', '[', ']', '"']:
        line = line.replace(separator, ' ')
    for word in line.split():
        msgid = get_msgid_from_public_inbox_link(word)
        if msgid is not None:
            item_handlers.append(
                    ['- hkml thread %s' % msgid, text_viewer_menu_hkml_thread])
            item_handlers.append(
                    ['- hkml open %s' % msgid, text_viewer_menu_hkml_open])
    item_handlers.append(
            ['- save entire content as ...', text_viewer_menu_save_content])
    return item_handlers

def show_available_action_items_handler(c, slist):
    item_handlers = build_text_view_menu_item_handlers(slist)
    if len(item_handlers) == 0:
        slist.toast('no action item found')
        return
    lines = ['selected line: %s' % slist.lines[slist.focus_row], '',
             'focus an item below and press Enter', '']
    menu_list = ScrollableList(slist.screen, lines, get_menu_input_handlers())
    menu_list.parent_list = slist
    menu_list.set_menu_item_handlers(item_handlers)
    menu_list.draw()

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

def get_attach_files():
    answer = input('Do you want to attach files to the mail? [y/N] ')
    if answer.lower() != 'y':
        return []
    files = []
    while True:
        file_path = receive_file_path(for_read=True)
        if file_path is None:
            return []

        files.append(file_path)

        print()
        answer = input('Do you have more files to attach? [y/N] ')
        if answer.lower() != 'y':
            break
    return files

def reply_mail_handler(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return

    shell_mode_start(slist)
    files = get_attach_files()
    hkml_reply.reply(mail, attach_files=files, format_only=None)
    shell_mode_end(slist)

def forward_mail_handler(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return
    shell_mode_start(slist)
    files = get_attach_files()
    hkml_forward.forward(mail, attach_files=files)
    shell_mode_end(slist)

def mails_list_open_mail(c, slist):
    open_mail_handler(c, slist.parent_list)

def mails_list_reply(c, slist):
    reply_mail_handler(c, slist.parent_list)

def mails_list_list_thread(c, slist):
    list_thread_handler(c, slist.parent_list)

def mails_list_forward(c, slist):
    forward_mail_handler(c, slist.parent_list)

def mails_list_continue_draft(c, slist):
    mail = get_focused_mail(slist.parent_list)
    if mail is None:
        return
    shell_mode_start(slist)
    hkml_write.write_send_mail(
            draft_mail=mail, subject=None, in_reply_to=None, to=None,
            cc=None, body=None, attach=None, format_only=None)
    shell_mode_end(slist)

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

    shell_mode_start(slist)

    print('the mail has below tags:')
    for tag in tags:
        print('- %s' % tag)
    print()
    _ = input('Press <Enter> to return')
    shell_mode_end(slist)

def mails_list_add_tags(c, slist):
    mail = get_focused_mail(slist.parent_list)
    if mail is None:
        return
    shell_mode_start(slist)

    msgid = mail.get_field('message-id')
    tags_map = hkml_tag.read_tags_file()
    if msgid in tags_map:
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
    shell_mode_end(slist)

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

    shell_mode_start(slist)

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
    shell_mode_end(slist)

def mails_list_check_patch(c, slist):
    shell_mode_start(slist)
    hkml_patch.main(argparse.Namespace(
        hkml_dir=None, command='patch', dont_add_cv=False, action='check',
        mail='%d' % focused_mail_idx(
            slist.parent_list.lines, slist.parent_list.focus_row),
        checker=None))
    print()
    _ = input('Press <Enter> to return to hkml')
    shell_mode_end(slist)

def mails_list_apply_patch(c, slist):
    shell_mode_start(slist)
    hkml_patch.main(argparse.Namespace(
        hkml_dir=None, command='patch', dont_add_cv=False, action='apply',
        mail='%d' % focused_mail_idx(
            slist.parent_list.lines, slist.parent_list.focus_row),
        repo='./'))
    print()
    _ = input('Press <Enter> to return to hkml')
    shell_mode_end(slist)

def mails_list_export(c, slist):
    idx = focused_mail_idx(slist.parent_list.lines,
                           slist.parent_list.focus_row)
    shell_mode_start(slist)
    print('Focused mail: %d' % idx)
    print()
    print('1. Export only focused mail')
    print('2. Export a range of mails of the list')
    print('3. Export all mails of the list')
    print()
    answer = input('Select: ')
    try:
        answer = int(answer)
    except:
        print('wrong input.  Return to hkml')
        time.sleep(1)
        shell_mode_end(slist)

    if answer == 1:
        export_range = [idx, idx + 1]
    elif answer == 2:
        answer = input(
                'Enter starting/ending index (inclusive) of mails to export: ')
        try:
            export_range = [int(x) for x in answer.split()]
            if len(export_range) != 2:
                print('wrong input.  Return to hkml')
                time.sleep(1)
                shell_mode_end(slist)
            export_range[1] += 1    # export receives half-open range
        except:
            print('wrong input.  Return to hkml')
            time.sleep(1)
            shell_mode_end(slist)
    else:
        export_range = None

    file_name = receive_file_path(for_read=False)
    if file_name is None:
        shell_mode_end(slist)
        return
    hkml_export.main(argparse.Namespace(
        hkml_dir=None, command='export', export_file=file_name,
        range=export_range))
    print()
    _ = input('Completed.  Press <Enter> to return to hkml')
    shell_mode_end(slist)

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

def mails_list_save(c, slist):
    shell_mode_start(slist)
    save_as('\n'.join(slist.parent_list.lines))
    shell_mode_end(slist)

mails_list_menu = [
        ['- open', mails_list_open_mail],
        ['- reply', mails_list_reply],
        ['- list complete thread', mails_list_list_thread],
        ['- forward', mails_list_forward],
        ['- continue draft writing', mails_list_continue_draft],
        ['- show tags', mails_list_show_tags],
        ['- add tags', mails_list_add_tags],
        ['- remove tags', mails_list_remove_tags],
        ['- check patch', mails_list_check_patch],
        ['- apply patch', mails_list_apply_patch],
        ['- export as an mbox file', mails_list_export],
        ['- save list text as ...', mails_list_save],
        ]

def get_menu_input_handlers():
    return scrollable_list_default_handlers() + [
            InputHandler(['\n'], menu_selection_handler,
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
    menu_list = ScrollableList(
            slist.screen, menu_lines, get_menu_input_handlers())
    menu_list.parent_list = slist
    menu_list.set_menu_item_handlers(mails_list_menu)
    menu_list.draw()

def get_mails_list_input_handlers():
    return scrollable_list_default_handlers() + [
            InputHandler(['o', '\n'], open_mail_handler, 'open focused mail'),
            InputHandler(['r'], reply_mail_handler, 'reply focused mail'),
            InputHandler(['f'], forward_mail_handler, 'forward focused mail'),
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
    slist.draw()
    return slist

def view(text, mail_idx_key_map):
    try:
        slist = curses.wrapper(__view, text, mail_idx_key_map)
    except Exception as e:
        if len(e.args) == 2 and e.args[0] == 'terminate hkml':
            slist = e.args[1]
        else:
            raise e
    print('\n'.join(slist.last_drawn))
