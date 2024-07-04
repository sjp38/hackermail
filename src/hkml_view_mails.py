# SPDX-License-Identifier: GPL-2.0

import argparse

import hkml_cache
import hkml_export
import hkml_forward
import hkml_list
import hkml_open
import hkml_patch
import hkml_reply
import hkml_tag
import hkml_thread
import hkml_view
import hkml_view_text
import hkml_write

# mails list

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
    mail_idx_key_map = slist.data
    if not mail_idx in mail_idx_key_map:
        slist.toast('wrong index?')
        return None
    mail_key = mail_idx_key_map[mail_idx]
    mail = hkml_cache.get_mail(key=mail_key)
    if mail is None:
        slist.toast('mail not cached?')
        return None
    return mail

def open_focused_mail(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return

    _, cols = slist.screen.getmaxyx()
    lines = hkml_open.mail_display_str(mail, cols).split('\n')
    hkml_view_text.show_text_viewer(slist.screen, lines)

def get_attach_files():
    answer = input('Do you want to attach files to the mail? [y/N] ')
    if answer.lower() != 'y':
        return []
    files = []
    while True:
        file_path = hkml_view.receive_file_path(for_read=True)
        if file_path is None:
            return []

        files.append(file_path)

        print()
        answer = input('Do you have more files to attach? [y/N] ')
        if answer.lower() != 'y':
            break
    return files

def reply_mail(slist, mail):
    hkml_view.shell_mode_start(slist)
    files = get_attach_files()
    hkml_reply.reply(mail, attach_files=files, format_only=None)
    hkml_view.shell_mode_end(slist)

def reply_focused_mail(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return

    reply_mail(slist, mail)

def forward_mail(slist, mail):
    hkml_view.shell_mode_start(slist)
    files = get_attach_files()
    hkml_forward.forward(mail, attach_files=files)
    hkml_view.shell_mode_end(slist)

def forward_focused_mail(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return
    forward_mail(mail, slist)

def list_thread_of_focused_mail(c, slist):
    thread_txt, mail_idx_key_map = hkml_thread.thread_str(
            '%d' % focused_mail_idx(slist.lines, slist.focus_row),
            False, False)
    hkml_cache.writeback_mails()
    hkml_list.cache_list_str('thread_output', thread_txt, mail_idx_key_map)

    show_mails_list(slist.screen, thread_txt.split('\n'), mail_idx_key_map)

def open_parent_focused_mail(c, slist):
    open_focused_mail(c, slist.parent_list)

def reply_parent_focused_mail(c, slist):
    reply_focused_mail(c, slist.parent_list)

def list_parent_focused_thread(c, slist):
    list_thread_of_focused_mail(c, slist.parent_list)

def forward_parent_focused_mail(c, slist):
    forward_focused_mail(c, slist.parent_list)

def write_mail_draft(slist, mail):
    hkml_view.shell_mode_start(slist)
    hkml_write.write_send_mail(
            draft_mail=mail, subject=None, in_reply_to=None, to=None,
            cc=None, body=None, attach=None, format_only=None)
    hkml_view.shell_mode_end(slist)

def write_parent_focused_draft(c, slist):
    mail = get_focused_mail(slist.parent_list)
    if mail is None:
        return
    write_mail_draft(slist, mail)

def manage_tags_of_mail(slist, mail):
    msgid = mail.get_field('message-id')
    tags_map = hkml_tag.read_tags_file()
    hkml_view.shell_mode_start(slist)

    if msgid in tags_map:
        tags = tags_map[msgid]['tags']
    else:
        tags = []
    if len(tags) > 0:
        print('the mail (\"%s\") has below tags:' % mail.subject)
        for tag in tags:
            print('- %s' % tag)
        print()
    print('What do you want to do?')
    print('1. Add tags')
    print('2. Remove tags')
    answer = input('Enter your selection (enter \'cancel_tag\' to cancel): ')
    if answer == 'cancel_tag':
        _ = input('Canceled.  Press enter to return')
        hkml_view.shell_mode_end(slist)
        return
    if not answer in ['1', '2']:
        _ = input('Wrong input.  It should be 1 or 2.  Enter to return.')
        hkml_view.shell_mode_end(slist)
        return

    if answer == '1':
        prompt = ' '.join(['Enter tags to add, separated by white spaces',
                           '(enter \'cancel_tag\' to cancel): '])
        tags = input(prompt).split()
        if 'cancel_tag' in tags:
            _ = input('Canceled.  Press enter to return')
            hkml_view.shell_mode_end(slist)
            return
        hkml_tag.do_add_tags(mail, tags)
    elif answer == '2':
        prompt = ' '.join(
                ['Enter tags to remove, separted by white spaces',
                 '(enter \'cancel_tag\' to cancel): '])
        tags_to_remove = input(prompt).split()
        if 'cancel_tag' in tags_to_remove:
            _ = input('Canceled.  Press enter to return')
            hkml_view.shell_mode_end(slist)
            return
        for tag in tags_to_remove:
            if not tag in tags:
                print('the mail is not tagged as %s' % tag)
                _ = input('Canceled.  Press enter to return')
                hkml_view.shell_mode_end(slist)
        hkml_tag.do_remove_tags(mail, tags_to_remove)
    else:
        raise Exception('this cannot happen')
    _ = input('Done.  Press enter to return')
    hkml_view.shell_mode_end(slist)

def manage_tags_of_parent_focused_mail(c, slist):
    mail = get_focused_mail(slist.parent_list)
    if mail is None:
        return
    manage_tags_of_mail(slist, mail)

def handle_patches_of_parent_focused_mail(c, slist):
    hkml_view.shell_mode_start(slist)
    mail = get_focused_mail(slist.parent_list)
    if mail is None:
        return
    print('Handle the mail (\'%s\') as patch[es].' % mail.subject)
    print()
    print('1. check patch[es]')
    print('2. apply patch[es]')
    print()
    answer = input('Select (enter \'cancel_patch\' to cancel): ')
    if answer == 'cancel_patch':
        _ = input('Canceled.  Press enter to return')
        hkml_view.shell_mode_end(slist)
        return

    if answer == '1':
        hkml_patch.main(argparse.Namespace(
            hkml_dir=None, command='patch', dont_add_cv=False, action='check',
            mail='%d' % focused_mail_idx(
                slist.parent_list.lines, slist.parent_list.focus_row),
            checker=None))
    elif answer == '2':
        hkml_patch.main(argparse.Namespace(
            hkml_dir=None, command='patch', dont_add_cv=False, action='apply',
            mail='%d' % focused_mail_idx(
                slist.parent_list.lines, slist.parent_list.focus_row),
            repo='./'))
    else:
        raise Exception('this cannot happen')
    print()
    _ = input('Done.  Press <Enter> to return to hkml')
    hkml_view.shell_mode_end(slist)

def export_mails_of_parent(c, slist):
    idx = focused_mail_idx(slist.parent_list.lines,
                           slist.parent_list.focus_row)
    hkml_view.shell_mode_start(slist)
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
        hkml_view.shell_mode_end(slist)

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
                hkml_view.shell_mode_end(slist)
            export_range[1] += 1    # export receives half-open range
        except:
            print('wrong input.  Return to hkml')
            time.sleep(1)
            hkml_view.shell_mode_end(slist)
    else:
        export_range = None

    file_name = hkml_view.receive_file_path(for_read=False)
    if file_name is None:
        hkml_view.shell_mode_end(slist)
        return
    hkml_export.main(argparse.Namespace(
        hkml_dir=None, command='export', export_file=file_name,
        range=export_range))
    print()
    _ = input('Completed.  Press <Enter> to return to hkml')
    hkml_view.shell_mode_end(slist)

def get_mails_list_menu():
    return [
        ['- continue draft writing', write_parent_focused_draft],
        ['- manage tags', manage_tags_of_parent_focused_mail],
        ['- handle as patches', handle_patches_of_parent_focused_mail],
        ['- export as an mbox file', export_mails_of_parent],
        hkml_view.save_parent_content_menu_item_handler,
        ['- open', open_parent_focused_mail],
        ['- reply', reply_parent_focused_mail],
        ['- list complete thread', list_parent_focused_thread],
        ['- forward', forward_parent_focused_mail],
        ]

def show_mails_list_menu(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return
    menu_lines = [
            'selected mail: %s' % mail.subject,
            '',
            'focus an item below and press Enter',
            '']
    menu_list = hkml_view.ScrollableList(slist.screen, menu_lines, None)
    menu_list.set_menu_item_handlers(slist, get_mails_list_menu())
    menu_list.draw()

def get_mails_list_input_handlers():
    return [
            hkml_view.InputHandler(
                ['o', '\n'], open_focused_mail, 'open focused mail'),
            hkml_view.InputHandler(
                ['r'], reply_focused_mail, 'reply focused mail'),
            hkml_view.InputHandler(
                ['f'], forward_focused_mail, 'forward focused mail'),
            hkml_view.InputHandler(['t'], list_thread_of_focused_mail,
                         'list complete thread'),
            hkml_view.InputHandler(['m'], show_mails_list_menu, 'open menu'),
            ]

def after_input_handle_callback(slist):
    mail_idx_key_map = slist.data
    if mail_idx_key_map is None:
        return
    _, last_mail_idx_key_map = hkml_list.get_last_mails_list()
    if mail_idx_key_map != last_mail_idx_key_map:
        hkml_list.cache_list_str(
                'thread_output', '\n'.join(slist.lines), mail_idx_key_map)

def show_mails_list(screen, text_lines, mail_idx_key_map):
    slist = hkml_view.ScrollableList(screen, text_lines,
                           get_mails_list_input_handlers())
    slist.data = mail_idx_key_map
    slist.after_input_handle_callback = after_input_handle_callback
    slist.draw()
    return slist
