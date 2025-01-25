# SPDX-License-Identifier: GPL-2.0

# text viewer

import os
import subprocess

import _hkml
import _hkml_list_cache
import hkml_cache
import hkml_list
import hkml_open
import hkml_view
import hkml_view_mails
import hkml_write

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

def menu_hkml_thread(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    hkml_view.shell_mode_end(slist)
    msgid = '<%s>' % text.split()[-1]
    args = hkml_view_mails.hkml_list_args_for_msgid(msgid)
    hkml_view_mails.gen_show_mails_list(slist.screen, args)
    hkml_view.shell_mode_start(slist)

def menu_hkml_open(data, answer):
    slist, selections, text = parse_menu_data(data, answer)
    hkml_view.shell_mode_end(slist)
    msgid = '<%s>' % text.split()[-1]
    args = hkml_view_mails.hkml_list_args_for_msgid(msgid)
    args.stdout = True  # to bypass dim_old suggestion
    list_data, err = hkml_list.args_to_mails_list_data( args)
    for idx, cache_key in list_data.mail_idx_key_map.items():
        mail = hkml_cache.get_mail(key=cache_key)
        if mail is None:
            continue
        if mail.get_field('message-id') == msgid:
            _, cols = slist.screen.getmaxyx()
            lines = hkml_open.mail_display_str(mail, cols).split('\n')
            show_text_viewer(slist.screen, lines)
            break
    hkml_view.shell_mode_start(slist)

def menu_open_file(data, answer, selection):
    slist, selections, text = parse_menu_data(data, answer)
    hkml_view.shell_mode_end(slist)
    file_path = selection.data
    with open(file_path, 'r') as f:
        lines = f.read().split('\n')
    show_text_viewer(slist.screen, lines)
    hkml_view.shell_mode_start(slist)

def menu_open_file_editor(data, answer, selection):
    slist, selections, text = parse_menu_data(data, answer)
    file_path = selection.data
    hkml_write.open_editor(file_path, 'file')

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
                text='hkml open file %s' % word, handle_fn=None,
                handle_fn_v2=menu_open_file,
                data=word))
            selections.append(hkml_view.CliSelection(
                text='open %s with a text editor' % word, handle_fn=None,
                handle_fn_v2=menu_open_file_editor, data=word))
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
                'handle as patches', menu_handle_patches),
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

def text_color_callback(slist, line_idx):
    is_hunk = False
    for start, end in slist.hunk_lines:
        if start <= line_idx and line_idx < end:
            is_hunk = True
            break

    line = slist.lines[line_idx]
    if len(line) == 0:
        return hkml_view.normal_color
    if is_hunk:
        if line[0] == '+':
            return hkml_view.add_color
        elif line[0] == '-':
            return hkml_view.delete_color
    elif line[0] == '>':
        return hkml_view.original_color
    return hkml_view.normal_color

def hunk_length(lines, orig_content, new_content):
    length = 0
    for line in lines:
        if line.startswith('-'):
            orig_content -= 1
        elif line.startswith('+'):
            new_content -= 1
        elif line.startswith(' '):
            orig_content -= 1
            new_content -= 1
        else:
            return length
        length += 1

        if orig_content < 0 or new_content < 0 or \
                (orig_content == new_content == 0):
            return length

    return length

def hunk_lines(text_lines):
    indices = []
    idx = 0
    while idx < len(text_lines):
        line = text_lines[idx]
        if not line.startswith('@@'):
            idx += 1
            continue
        fields = line.split()
        # format: "@@ -l,s +l,s @@ optional section heading"
        if len(fields) < 4:
            idx += 1
            continue
        numbers = fields[1].split(',') + fields[2].split(',')
        if len(numbers) != 4:
            idx += 1
            continue
        try:
            numbers = [int(x) for x in numbers]
        except:
            idx += 1
            continue
        orig_content, new_content = numbers[1], numbers[3]
        hunk_len = hunk_length(text_lines[idx + 1:], orig_content, new_content)
        indices.append([idx + 1, idx + 1 + hunk_len])
        idx += hunk_len + 1
    return indices

def show_text_viewer(screen, text_lines, data=None, cursor_position=None):
    slist = hkml_view.ScrollableList(
            screen, text_lines, get_text_viewer_handlers(data))
    slist.data = data
    slist.hunk_lines = hunk_lines(text_lines)
    slist.color_callback = text_color_callback
    if cursor_position is not None:
        slist.focus_row, slist.focus_col = cursor_position
    slist.draw()
    return slist
