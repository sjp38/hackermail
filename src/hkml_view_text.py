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
    if slist.data is None:
        # tui menu
        line = slist.lines[slist.focus_row]
    else:
        # cli menu
        line = slist.data
    words = line.split()[1:]
    try:
        output = subprocess.check_output(
                words, stderr=subprocess.DEVNULL).decode().split('\n')
    except Exception as e:
        output = ['failed: %s' % e, '',
                  'wrong commit id, or you are not on the git repo?']
    show_text_viewer(slist.screen, output)

def parse_menu_data(data, answer):
    slist, selections = data
    text = selections[int(answer) - 1].text
    return slist, selections, text

def menu_exec_git(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    hkml_view.shell_mode_end(slist)
    words = text.split()
    try:
        output = subprocess.check_output(
                words, stderr=subprocess.DEVNULL).decode().split('\n')
    except Exception as e:
        output = ['failed: %s' % e, '',
                  'wrong commit id, or you are not on the git repo?']
    show_text_viewer(slist.screen, output)
    hkml_view.shell_mode_start(slist)

def get_thread_txt_mail_idx_key_map(msgid):
    thread_txt, mail_idx_key_map = hkml_thread.thread_str(msgid,
            False, False)
    hkml_cache.writeback_mails()
    hkml_list.cache_list_str('thread_output', thread_txt, mail_idx_key_map)
    return thread_txt, mail_idx_key_map

def text_viewer_menu_hkml_thread(c, slist):
    if slist.data is None:
        # tui menu
        line = slist.lines[slist.focus_row]
    else:
        # cli menu
        line = slist.data
    msgid = '<%s>' % line.split()[1:][-1]
    thread_txt, mail_idx_key_map = get_thread_txt_mail_idx_key_map(msgid)
    hkml_view_mails.show_mails_list(slist.screen, thread_txt.split('\n'),
                              mail_idx_key_map)

def menu_hkml_thread(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    hkml_view.shell_mode_end(slist)
    msgid = '<%s>' % text.split()[-1]
    thread_txt, mail_idx_key_map = get_thread_txt_mail_idx_key_map(msgid)
    hkml_view_mails.show_mails_list(slist.screen, thread_txt.split('\n'),
                              mail_idx_key_map)
    hkml_view.shell_mode_start(slist)

def text_viewer_menu_hkml_open(c, slist):
    if slist.data is None:
        # tui menu
        line = slist.lines[slist.focus_row]
    else:
        # cli menu
        line = slist.data
    msgid = '<%s>' % line.split()[1:][-1]
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

def menu_hkml_open(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    hkml_view.shell_mode_end(slist)
    msgid = '<%s>' % text.split()[-1]
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
    hkml_view.shell_mode_start(slist)

def text_viewer_menu_open_file(c, slist):
    if slist.data is None:
        # tui menu
        line = slist.lines[slist.focus_row]
    else:
        # cli menu
        line = slist.data
    file_path = line.split()[1:][-1]
    with open(file_path, 'r') as f:
        lines = f.read().split('\n')
    show_text_viewer(slist.screen, lines)

def menu_open_file(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    hkml_view.shell_mode_end(slist)
    file_path = text.split()[-1]
    with open(file_path, 'r') as f:
        lines = f.read().split('\n')
    show_text_viewer(slist.screen, lines)
    hkml_view.shell_mode_start(slist)

def text_viewer_menu_vim_file(c, slist):
    if slist.data is None:
        # tui menu
        line = slist.lines[slist.focus_row]
    else:
        # cli menu
        line = slist.data
    file_path = line.split()[1:][-1]
    hkml_view.shell_mode_start(slist)
    subprocess.call(['vim', file_path])
    hkml_view.shell_mode_end(slist)

def menu_vim_file(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    file_path = text.split()[-1]
    subprocess.call(['vim', file_path])

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

def menu_selections_for_commit(line):
    for separator in [',', '(', ')', '/', '[', ']', '"']:
        line = line.replace(separator, ' ')
    selections = []
    for word in line.split():
        if not is_git_hash(word):
            continue
        selections.append(
                hkml_view.CliSelection('git show %s' % word, menu_exec_git))
        selections.append(
                hkml_view.CliSelection(
                    'git log -n 5 %s' % word, menu_exec_git))
        selections.append(
                hkml_view.CliSelection(
                    'git log --oneline -n 64 %s' % word, menu_exec_git))
    return selections

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

def menu_selections_for_msgid(line):
    for separator in [',', '(', ')', '[', ']', '"']:
        line = line.replace(separator, ' ')
    selections = []
    for word in line.split():
        msgid = get_msgid_from_public_inbox_link(word)
        if msgid is None:
            continue
        selections.append(hkml_view.CliSelection(
            'hkml thread %s' % msgid, menu_hkml_thread))
        selections.append(hkml_view.CliSelection(
            'hkml open %s' % msgid, menu_hkml_open))
    return selections

def text_viewer_menu_exec_web(c, slist):
    # line is "- {lynx,w3m} url"
    if slist.data is None:
        # tui menu
        line = slist.lines[slist.focus_row]
    else:
        # cli menu
        line = slist.data
    cmd, url = line.split()[1:]
    hkml_view.shell_mode_start(slist)
    subprocess.call([cmd, url])
    hkml_view.shell_mode_end(slist)

def menu_exec_web(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    subprocess.call(text.split())

def add_menus_for_url(item_handlers, line):
    for separator in [',', '(', ')', '[', ']', '"']:
        line = line.replace(separator, ' ')
    for word in line.split():
        if not word.startswith('http://') and not word.startswith('https://'):
            continue
        try:
            subprocess.check_output(['which', 'lynx'])
            item_handlers.append(
                    ['- lynx %s' % word, text_viewer_menu_exec_web])
        except:
            # lynx not installed.
            pass
        try:
            subprocess.check_output(['which', 'w3m'])
            item_handlers.append(
                    ['- w3m %s' % word, text_viewer_menu_exec_web])
        except:
            # w3m not installed.
            pass

def menu_selections_for_url(line):
    for separator in [',', '(', ')', '[', ']', '"']:
        line = line.replace(separator, ' ')
    selections = []
    for word in line.split():
        if not word.startswith('http://') and not word.startswith('https://'):
            continue
        try:
            subprocess.check_output(['which', 'lynx'])
            selections.append(hkml_view.CliSelection(
                'lynx %s' % word, menu_exec_web))
        except:
            # lynx not installed.
            pass
        try:
            subprocess.check_output(['which', 'w3m'])
            selections.append(hkml_view.CliSelection(
                'w3m %s' % word, menu_exec_web))
        except:
            # w3m not installed.
            pass
    return selections

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

def menu_selections_for_files(line):
    for separator in [',', '(', ')', '[', ']', '"', ':']:
        line = line.replace(separator, ' ')

    found_files = {}
    selections = []
    for word in line.split():
        # file paths on diff starts with a/ and b/, e.g.,
        #
        # --- a/tools/testing/selftests/damon/damon_nr_regions.py
        # +++ b/tools/testing/selftests/damon/damon_nr_regions.py
        if word.startswith('a/') or word.startswith('b/'):
            word = word[2:]
        if not word in found_files and os.path.isfile(word):
            found_files[word] = True
            selections.append(hkml_view.CliSelection(
                'hkml open file %s' % word, menu_open_file))
            selections.append(hkml_view.CliSelection(
                'vim %s' % word, menu_vim_file))
    return selections

def reply_mail(c, slist):
    # maybe called from tui/cli menu
    if slist.parent_list is not None:
        slist = slist.parent_list
    mail = slist.data
    if mail is None or type(mail) is not _hkml.Mail:
        slist.toast('parent is not a mail?')
        return

    hkml_view_mails.reply_mail(slist, mail)

def menu_reply_mail(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    mail = slist.data
    hkml_view.shell_mode_end(slist)
    hkml_view_mails.reply_mail(slist, mail)
    hkml_view.shell_mode_start(slist)

def forward_mail(c, slist):
    # maybe called from tui/cli menu
    if slist.parent_list is not None:
        slist = slist.parent_list
    mail = slist.data
    if mail is None or type(mail) is not _hkml.Mail:
        slist.toast('parent is not a mail?')
        return

    hkml_view_mails.forward_mail(slist, mail)

def menu_forward_mail(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    mail = slist.data
    hkml_view.shell_mode_end(slist)
    hkml_view_mails.forward_mail(slist, mail)
    hkml_view.shell_mode_start(slist)

def write_draft_mail(c, slist):
    # maybe called from tui/cli menu
    if slist.parent_list is not None:
        slist = slist.parent_list
    mail = slist.data
    if mail is None or type(mail) is not _hkml.Mail:
        slist.toast('parent is not a mail?')
        return
    hkml_view_mails.write_mail_draft(slist, mail)

def menu_write_draft(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    mail = slist.data
    hkml_view.shell_mode_end(slist)
    hkml_view_mails.write_mail_draft(slist, mail)
    hkml_view.shell_mode_start(slist)

def manage_tags(c, slist):
    # maybe called from tui/cli menu
    if slist.parent_list is not None:
        slist = slist.parent_list
    mail = slist.data
    if mail is None or type(mail) is not _hkml.Mail:
        slist.toast('parent is not a mail?')
        return
    hkml_view_mails.manage_tags_of_mail(slist, mail)

def menu_manage_tags(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    mail = slist.data
    hkml_view_mails.manage_tags_of_mail(slist, mail)

def handle_patches(c, slist):
    if slist.parent_list is not None:
        slist = slist.parent_list
    mail = slist.data
    hkml_view.shell_mode_start(slist)
    hkml_view_mails.handle_patches_of_mail(mail)
    hkml_view.shell_mode_end(slist)

def menu_handle_patches(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    mail = slist.data
    hkml_view_mails.handle_patches_of_mail(mail)

def add_menus_for_mail(item_handlers, mail):
    item_handlers.append(
            ['- reply', reply_mail])
    item_handlers.append(
            ['- forward', forward_mail])
    item_handlers.append(['- continue draft writing', write_draft_mail])
    item_handlers.append(['- manage tags', manage_tags])
    item_handlers.append(['- handle as patches', handle_patches])

def menu_selections_for_mail():
    return [
            hkml_view.CliSelection('reply', menu_reply_mail),
            hkml_view.CliSelection('forward', menu_forward_mail),
            hkml_view.CliSelection(
                'continue draft writing', menu_write_draft),
            hkml_view.CliSelection('manage tags', menu_manage_tags),
            hkml_view.CliSelection(
                'hanlde as patches', menu_handle_patches),
            ]

def build_text_view_menu_item_handlers(slist):
    line = slist.lines[slist.focus_row]

    item_handlers = []
    add_menus_for_commit(item_handlers, line)
    add_menus_for_msgid(item_handlers, line)
    add_menus_for_url(item_handlers, line)
    add_menus_for_files(item_handlers, line)

    if type(slist.data) is _hkml.Mail:
        add_menus_for_mail(item_handlers, slist.data)

    item_handlers.append(hkml_view.save_parent_content_menu_item_handler)
    return item_handlers

def show_cli_text_viewer_menu(c, slist):
    def cli_handle_fn(data, answer):
        slist, item_handlers = data
        for idx, item_handler in enumerate(item_handlers):
            _, slist_handle_fn = item_handler
            if answer == '%d' % (idx + 1):
                hkml_view.shell_mode_end(slist)
                data_bak = slist.data
                slist.data = item_handler[0]
                slist_handle_fn('\n', slist)
                slist.data = data_bak
                hkml_view.shell_mode_start(slist)
                return

    item_handlers = build_text_view_menu_item_handlers(slist)
    selections = []
    for text, _ in item_handlers:
        if text.startswith('- '):
            text = text[2:]
        selections.append(hkml_view.CliSelection(text, cli_handle_fn))

    hkml_view.shell_mode_start(slist)
    q = hkml_view.CliQuestion(
            desc='selected line: %s' % slist.lines[slist.focus_row],
            prompt='Enter menu item number')
    slist.parent_list = slist
    q.ask_selection(
            [slist, item_handlers], selections)
    hkml_view.shell_mode_end(slist)

def menu_selections(slist):
    line = slist.lines[slist.focus_row]

    selections = menu_selections_for_commit(line)
    selections += menu_selections_for_msgid(line)
    selections += menu_selections_for_url(line)
    selections += menu_selections_for_files(line)

    if type(slist.data) is _hkml.Mail:
        selections += menu_selections_for_mail()
    return selections

def show_text_viewer_menu(c, slist):
    hkml_view.shell_mode_start(slist)
    q = hkml_view.CliQuestion(
            desc='selected line: %s' % slist.lines[slist.focus_row],
            prompt='Enter menu item number')
    selections = menu_selections(slist)
    q.ask_selection(data=[slist, selections], selections=selections)
    hkml_view.shell_mode_end(slist)

def get_text_viewer_handlers(data):
    if type(data) is _hkml.Mail:
        handlers = [
                hkml_view.InputHandler(['r'], reply_mail, 'reply'),
                hkml_view.InputHandler(['f'], forward_mail, 'forward'),
                ]
    else:
        handlers = []
    return handlers + [
            hkml_view.InputHandler(
                ['m'], show_text_viewer_menu, 'open menu'),
            ]

def show_text_viewer(screen, text_lines, data=None):
    slist = hkml_view.ScrollableList(
            screen, text_lines, get_text_viewer_handlers(data))
    slist.data = data
    slist.draw()
    return slist
