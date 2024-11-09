# SPDX-License-Identifier: GPL-2.0

# text viewer

import os
import subprocess

import _hkml
import _hkml_list_cache
import hkml_cache
import hkml_list
import hkml_open
import hkml_thread
import hkml_view
import hkml_view_mails

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
    _hkml_list_cache.set_item('thread_output', thread_txt, mail_idx_key_map)
    return thread_txt, mail_idx_key_map, None

def menu_hkml_thread(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    hkml_view.shell_mode_end(slist)
    msgid = '<%s>' % text.split()[-1]
    hkml_view_mails.gen_show_mails_list(
            slist.screen,
            hkml_view_mails.MailsListDataGenerator(
                get_thread_txt_mail_idx_key_map, msgid))
    hkml_view.shell_mode_start(slist)

def menu_hkml_open(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    hkml_view.shell_mode_end(slist)
    msgid = '<%s>' % text.split()[-1]
    thread_txt, mail_idx_key_map, err = get_thread_txt_mail_idx_key_map(msgid)
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

def menu_exec_web(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    subprocess.call(text.split())

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
