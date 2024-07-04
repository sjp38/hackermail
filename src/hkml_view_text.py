# SPDX-License-Identifier: GPL-2.0

# text viewer

import os
import subprocess

import _hkml
import hkml_cache
import hkml_list
import hkml_open
import hkml_thread
import hkml_view
import hkml_view_mails

def text_viewer_menu_exec_git(c, slist):
    words = slist.lines[slist.focus_row].split()[1:]
    try:
        output = subprocess.check_output(
                words, stderr=subprocess.DEVNULL).decode().split('\n')
    except Exception as e:
        output = ['failed: %s' % e, '',
                  'wrong commit id, or you are not on the git repo?']
    show_text_viewer(slist.screen, output)

def get_thread_txt_mail_idx_key_map(msgid):
    thread_txt, mail_idx_key_map = hkml_thread.thread_str(msgid,
            False, False)
    hkml_cache.writeback_mails()
    hkml_list.cache_list_str('thread_output', thread_txt, mail_idx_key_map)
    return thread_txt, mail_idx_key_map

def text_viewer_menu_hkml_thread(c, slist):
    msgid = '<%s>' % slist.lines[slist.focus_row].split()[1:][-1]
    thread_txt, mail_idx_key_map = get_thread_txt_mail_idx_key_map(msgid)
    hkml_view_mails.show_mails_list(slist.screen, thread_txt.split('\n'),
                              mail_idx_key_map)

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
            show_text_viewer(slist.screen, lines)
            break

def text_viewer_menu_open_file(c, slist):
    file_path = slist.lines[slist.focus_row].split()[1:][-1]
    with open(file_path, 'r') as f:
        lines = f.read().split('\n')
    show_text_viewer(slist.screen, lines)

def text_viewer_menu_vim_file(c, slist):
    file_path = slist.lines[slist.focus_row].split()[1:][-1]
    hkml_view.shell_mode_start(slist)
    subprocess.call(['vim', file_path])
    hkml_view.shell_mode_end(slist)

def is_git_hash(word):
    if len(word) < 10:
        return False
    for c in word:
        if c not in '0123456789abcdef':
            return False
    return True

def add_menus_for_commit(item_handlers, line):
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

def add_menus_for_msgid(item_handlers, line):
    for separator in [',', '(', ')', '[', ']', '"']:
        line = line.replace(separator, ' ')
    for word in line.split():
        msgid = get_msgid_from_public_inbox_link(word)
        if msgid is not None:
            item_handlers.append(
                    ['- hkml thread %s' % msgid, text_viewer_menu_hkml_thread])
            item_handlers.append(
                    ['- hkml open %s' % msgid, text_viewer_menu_hkml_open])

def add_menus_for_files(item_handlers, line):
    for separator in [',', '(', ')', '[', ']', '"']:
        line = line.replace(separator, ' ')

    found_files = {}
    for word in line.split():
        # file paths on diff starts with a/ and b/, e.g.,
        #
        # --- a/tools/testing/selftests/damon/damon_nr_regions.py
        # +++ b/tools/testing/selftests/damon/damon_nr_regions.py
        if word.startswith('a/') or word.startswith('b/'):
            word = word[2:]
        if not word in found_files and os.path.isfile(word):
            found_files[word] = True
            item_handlers.append(
                    ['- hkml open file %s' % word, text_viewer_menu_open_file])
            item_handlers.append(
                    ['- vim %s' % word, text_viewer_menu_vim_file])

def reply_parent_mail(c, slist):
    mail = _hkml.Mail(mbox='\n'.join(slist.parent_list.lines))
    if mail.broken():
        slist.toast('parent is not a mail?')
        return

    hkml_view_mails.reply_mail(slist, mail)

def add_menus_for_mail(item_handlers, mail):
    item_handlers.append(
            ['- reply', reply_parent_mail])

def build_text_view_menu_item_handlers(slist):
    line = slist.lines[slist.focus_row]

    item_handlers = []
    add_menus_for_commit(item_handlers, line)
    add_menus_for_msgid(item_handlers, line)
    add_menus_for_files(item_handlers, line)

    mail = _hkml.Mail(mbox='\n'.join(slist.lines))
    if not mail.broken():
        add_menus_for_mail(item_handlers, mail)

    item_handlers.append(hkml_view.save_parent_content_menu_item_handler)
    return item_handlers

def show_text_viewer_menu(c, slist):
    item_handlers = build_text_view_menu_item_handlers(slist)
    lines = ['selected line: %s' % slist.lines[slist.focus_row], '',
             'focus an item below and press Enter', '']
    menu_list = hkml_view.ScrollableList(slist.screen, lines, None)
    menu_list.set_menu_item_handlers(slist, item_handlers)
    menu_list.draw()

def get_text_viewer_handlers():
    return [
            hkml_view.InputHandler(
                ['m', '\n'], show_text_viewer_menu, 'open menu')
                ]

def show_text_viewer(screen, text_lines):
    slist = hkml_view.ScrollableList(
            screen, text_lines, get_text_viewer_handlers())
    slist.draw()
    return slist
