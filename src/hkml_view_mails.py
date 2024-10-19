# SPDX-License-Identifier: GPL-2.0

import argparse
import curses
import datetime

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

def get_mail_of_row(slist, row):
    # returns mail and error string
    mail_idx = focused_mail_idx(slist.lines, row)
    if mail_idx is None:
        return None, 'no mail focused?'
    mail_idx = '%d' % mail_idx
    mail_idx_key_map = slist.data['mail_idx_key_map']
    if not mail_idx in mail_idx_key_map:
        return None, 'wrong index?'
    mail_key = mail_idx_key_map[mail_idx]
    mail = hkml_cache.get_mail(key=mail_key)
    if mail is None:
        return None, 'mail not cached?'
    return mail, None

def get_focused_mail(slist):
    mail, err = get_mail_of_row(slist, slist.focus_row)
    if err is not None:
        slist.toast(err)
        return None
    return mail

def open_focused_mail(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return

    _, cols = slist.screen.getmaxyx()
    lines = hkml_open.mail_display_str(mail, cols).split('\n')
    hkml_view_text.show_text_viewer(slist.screen, lines, data=mail)

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
    forward_mail(slist, mail)

def get_thread_txt_mail_idx_key_map(msgid):
    thread_txt, mail_idx_key_map = hkml_thread.thread_str(
            msgid, False, False)
    hkml_cache.writeback_mails()
    hkml_list.cache_list_str('thread_output', thread_txt, mail_idx_key_map)
    return thread_txt, mail_idx_key_map, None

def list_thread_of_focused_mail(c, slist):
    msgid = get_focused_mail(slist).get_field('message-id')
    gen_show_mails_list(
            slist.screen, MailsListDataGenerator(
                get_thread_txt_mail_idx_key_map, msgid))

def refresh_list(slist):
    comment_lines = []
    for line in slist.lines:
        if line.startswith('#'):
            comment_lines.append(line)

    collapsed_mails = slist.data['collapsed_mails']

    mails = get_mails(slist)
    decorator = hkml_list.MailListDecorator(None)
    decorator.collapse = False
    decorator.show_url = False
    _, cols = slist.screen.getmaxyx()
    decorator.cols = int(cols * 0.9)

    text = '\n'.join(hkml_list.fmt_mails_text(
        mails, decorator, collapsed_mails))
    slist.lines = comment_lines + text.split('\n')
    slist.focus_row = min(slist.focus_row, len(slist.lines) - 1)
    slist.screen.clear()

def collapse_focused_thread(c, slist):
    if not 'collapsed_mails' in slist.data:
        slist.data['collapsed_mails'] = {}
    collapsed_mails = slist.data['collapsed_mails']

    collapsed_mails[focused_mail_idx(slist.lines, slist.focus_row)] = True
    refresh_list(slist)

def expand_focused_thread(c, slist):
    if not 'collapsed_mails' in slist.data:
        return
    collapsed_mails = slist.data['collapsed_mails']
    del collapsed_mails[focused_mail_idx(slist.lines, slist.focus_row)]
    refresh_list(slist)

def write_mail_draft(slist, mail):
    hkml_view.shell_mode_start(slist)
    hkml_write.write_send_mail(
            draft_mail=mail, subject=None, in_reply_to=None, to=None,
            cc=None, body=None, attach=None, format_only=None)
    hkml_view.shell_mode_end(slist)

def do_add_tags(data, selection):
    mail, tags = data
    prompt = ' '.join(['Enter tags to add, separated by white spaces',
                       '(enter \'cancel_tag\' to cancel): '])
    tags = input(prompt).split()
    if 'cancel_tag' in tags:
        _ = input('Canceled.  Press enter to return')
        return 'canceled'
    hkml_tag.do_add_tags(mail, tags)

def do_remove_tags(data, selection):
    mail, tags = data
    prompt = ' '.join(
            ['Enter tags to remove, separted by white spaces',
             '(enter \'cancel_tag\' to cancel): '])
    tags_to_remove = input(prompt).split()
    if 'cancel_tag' in tags_to_remove:
        _ = input('Canceled.  Press enter to return')
        return 'canceled'
    for tag in tags_to_remove:
        if not tag in tags:
            print('the mail is not tagged as %s' % tag)
            _ = input('Canceled.  Press enter to return')
            return 'the mail is not tagged as %s' % tag
    hkml_tag.do_remove_tags(mail, tags_to_remove)

def manage_tags_of_mail(slist, mail):
    msgid = mail.get_field('message-id')
    tags_map = hkml_tag.read_tags_file()
    hkml_view.shell_mode_start(slist)

    if msgid in tags_map:
        tags = tags_map[msgid]['tags']
    else:
        tags = []

    msg_lines = ['Handle tags of the mail ("%s")' % mail.subject]
    if len(tags) > 0:
        msg_lines.append('')
        msg_lines.append('the mail has below tags:')
        for tag in tags:
            msg_lines.append('- %s' % tag)
    q = hkml_view.CliQuestion(desc='\n'.join(msg_lines), prompt='Select')
    q.ask_selection(
            data=[mail, tags],
            selections=[
                hkml_view.CliSelection('Add tags', do_add_tags),
                hkml_view.CliSelection('Remove tags', do_remove_tags)])
    hkml_view.shell_mode_end(slist)

def do_check_patch(data, selection):
    mail = data
    err = hkml_patch.apply_action_to_mails(mail, argparse.Namespace(
        hkml_dir=None, command='patch', dont_add_cv='ask', action='check',
        checker=None))
    if err is not None:
        hkml_view.cli_any_input('applying action failed (%s)' % err)

def do_apply_patch(data, selection):
    mail = data
    err = hkml_patch.apply_action_to_mails(mail, argparse.Namespace(
        hkml_dir=None, command='patch', dont_add_cv='ask', action='apply',
        repo='./'))
    if err is not None:
        hkml_view.cli_any_input('applying action failed (%s)' % err)

def do_export_patch(data, selection):
    mail = data
    err = hkml_patch.apply_action_to_mails(mail, argparse.Namespace(
        hkml_dir=None, command='patch', dont_add_cv='ask', action='export',
        repo='./'))
    if err is not None:
        hkml_view.cli_any_input('applying action failed (%s)' % err)

def handle_patches_of_mail(mail, list_mails=None):
    msgid = mail.get_field('message-id')
    if list_mails is None:
        list_mails, err = hkml_thread.get_thread_mails_from_web(msgid)
        if err is not None:
            hkml_view.cli_any_input('get_thread_mails_from_web() failed (%s)' %
                                    err)
            return
    threads = hkml_list.threads_of(list_mails)
    mail_with_replies = None
    for thread_root_mail in threads:
        mail_with_replies = hkml_patch.find_mail_from_thread(
                thread_root_mail, msgid)
        if mail_with_replies is not None:
            break
    if mail_with_replies is None:
        hkml_view.cli_any_input('getting mail with replies failed.')
        return
    mail = mail_with_replies

    q = hkml_view.CliQuestion(
            desc='Handle the mail (\'%s\') as patch[es].' % mail.subject,
            prompt='Enter the item number')
    q.ask_selection(
            data=mail,
            selections=[
                hkml_view.CliSelection('check patch[es]', do_check_patch),
                hkml_view.CliSelection('apply patch[es]', do_apply_patch),
                hkml_view.CliSelection('export patch[es]', do_export_patch)],
            notify_completion=True)

def __set_prdepth(mail, depth):
    mail.prdepth = depth
    for reply in mail.replies:
        __set_prdepth(reply, depth + 1)

def set_prdepth(mails):
    threads = hkml_list.threads_of(mails)
    for mail in threads:
        __set_prdepth(mail, 0)

def get_mails(slist):
    mails = []
    mail_idx_key_map = slist.data['mail_idx_key_map']
    for mail_idx in mail_idx_key_map:
        mail_key = mail_idx_key_map[mail_idx]
        mail = hkml_cache.get_mail(key=mail_key)
        mail.pridx = int(mail_idx)
        mail.filtered_out = False
        mails.append(mail)
    set_prdepth(mails)
    return mails

def do_export(data, answer):
    slist, idx = data
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
                err = 'wrong number of inputs.'
                hkml_view.cli_any_input(err)
                return err
            export_range[1] += 1    # export receives half-open range
        except:
            err = 'wrong input.'
            hkml_view.cli_any_input(err)
            return err
    else:
        export_range = None

    file_name = hkml_view.receive_file_path(for_read=False)
    if file_name is None:
        return 'file unselected'
    hkml_export.main(argparse.Namespace(
        hkml_dir=None, command='export', export_file=file_name,
        range=export_range))
    print()

def export_mails(c, slist):
    idx = focused_mail_idx(slist.lines, slist.focus_row)
    hkml_view.shell_mode_start(slist)

    q = hkml_view.CliQuestion(desc='Focused mail: %d' % idx)
    q.ask_selection(
            data=[slist, idx],
            selections=[
                hkml_view.CliSelection('Export only focused mail', do_export),
                hkml_view.CliSelection(
                    'Export a range of mails of the list', do_export),
                hkml_view.CliSelection(
                    'Export all mails of the list', do_export)],
                notify_completion=True)
    hkml_view.shell_mode_end(slist)

def menu_open_mail(mail_slist, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    open_focused_mail(None, slist)
    hkml_view.shell_mode_start(slist)

def menu_list_thread(mail_slist, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    list_thread_of_focused_mail(None, slist)
    hkml_view.shell_mode_start(slist)

def menu_collapse_expand(mail_slist, selection):
    mail, slist = mail_slist
    if ('collapsed_mails' in slist.data and
        focused_mail_idx( slist.lines, slist.focus_row) in
        slist.data['collapsed_mails']):
        hkml_view.shell_mode_end(slist)
        expand_focused_thread(None, slist)
        hkml_view.shell_mode_start(slist)
        return
    hkml_view.shell_mode_end(slist)
    collapse_focused_thread(None, slist)
    hkml_view.shell_mode_start(slist)

class MailDisplayEffect:
    min_date = None
    max_date = None
    effect = None

    def eligible(self, mail):
        if self.min_date is not None:
            if self.min_date != 'min' and mail.date < self.min_date:
                return False
        if self.max_date is not None:
            if self.max_date != 'max' and mail.date > self.max_date:
                return False
        return True

    def effect_str(self):
        return {
                hkml_view.ScrollableList.effect_normal: 'no effect',
                hkml_view.ScrollableList.effect_dim: 'dim',
                hkml_view.ScrollableList.effect_bold: 'bold',
                hkml_view.ScrollableList.effect_italic: 'italic',
                hkml_view.ScrollableList.effect_blink: 'blink',
                hkml_view.ScrollableList.effect_reverse: 'reverse',
                hkml_view.ScrollableList.effect_underline: 'underline',
                }[self.effect]

    def __str__(self):
        return '\n'.join([
            'minimum date: %s' % self.min_date,
            'maximum date: %s' % self.max_date,
            'effect: %s' % self.effect_str()
            ])

    def interactive_setup_dates(self):
        q = hkml_view.CliQuestion(
                prompt='Minimum date (inclusive, YYYY MM DD HH MM or min)')
        answer, _, err = q.ask_input(data=None, handle_fn=None)
        if err is not None:
            return
        if answer == 'min':
            self.min_date = answer
        else:
            try:
                self.min_date = datetime.datetime(
                        *[int(x) for x in answer.split()]).astimezone()
            except Exception as e:
                hkml_view.cli_any_input(e)
                return
        q = hkml_view.CliQuestion(
                prompt='Maximum date (inclusive, YYYY MM DD HH MM or max)')
        answer, _, err = q.ask_input(data=None, handle_fn=None)
        if err is not None:
            return
        if answer == 'max':
            self.max_date = answer
        else:
            try:
                self.max_date = datetime.datetime(
                        *[int(x) for x in answer.split()]).astimezone()
            except Exception as e:
                hkml_view.cli_any_input(e)
                return

    def __init__(self, interactive):
        if interactive is False:
            return
        q = hkml_view.CliQuestion(
                desc='Select the display effect to apply.', prompt=None)

        def handle_selection(data, answer):
            rule, selections = data
            rule.effect = selections[int(answer) - 1].data

        selections=[
                hkml_view.CliSelection(
                    text='Normal', handle_fn=handle_selection,
                    data=hkml_view.ScrollableList.effect_normal),
                hkml_view.CliSelection(
                    text='Dim', handle_fn=handle_selection,
                    data=hkml_view.ScrollableList.effect_dim),
                hkml_view.CliSelection(
                    text='Bold', handle_fn=handle_selection,
                    data=hkml_view.ScrollableList.effect_bold),
                hkml_view.CliSelection(
                    text='Italic', handle_fn=handle_selection,
                    data=hkml_view.ScrollableList.effect_italic),
                hkml_view.CliSelection(
                    text='Blink', handle_fn=handle_selection,
                    data=hkml_view.ScrollableList.effect_blink),
                hkml_view.CliSelection(
                    text='Reverse', handle_fn=handle_selection,
                    data=hkml_view.ScrollableList.effect_reverse),
                hkml_view.CliSelection(
                    text='Underline', handle_fn=handle_selection,
                    data=hkml_view.ScrollableList.effect_underline),
                ]
        _, selection, err = q.ask_selection(
                data=[self, selections], selections=selections)
        if err is not None:
            return
        self.interactive_setup_dates()

def menu_effect_mails(mail_slist, selection):
    print('Apply a display effect to specific mails.')
    print()
    mail, slist = mail_slist
    if 'mails_effects' in slist.data:
        print('current display effect:')
        print('%s' % slist.data['mails_effects'])
        print()

    slist.data['mails_effects'] = MailDisplayEffect(interactive=True)

def menu_reply_mail(mail_slist, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    reply_focused_mail(None, slist)
    hkml_view.shell_mode_start(slist)

def menu_forward_mail(mail_slist, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    forward_focused_mail(None, slist)
    hkml_view.shell_mode_start(slist)

def menu_write_draft(mail_slist, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    write_mail_draft(slist, mail)
    hkml_view.shell_mode_start(slist)

def menu_manage_tags(mail_slist, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    manage_tags_of_mail(slist, mail)
    hkml_view.shell_mode_start(slist)

def menu_handle_patches(mail_slist, selection):
    mail, slist = mail_slist
    handle_patches_of_mail(mail, get_mails(slist))

def menu_refresh_mails(mail_slist, selection):
    mail, slist = mail_slist
    data_generator = slist.data['data_generator']
    gen_args = data_generator.args
    if type(gen_args) is argparse.Namespace and gen_args.fetch is False:
        answer = input('"--fetch" is unset.  Set it? [Y/n] ')
        if answer.lower() != 'n':
            gen_args.fetch = True

    text, mail_idx_key_map, display_rule, err = data_generator.generate()
    if err is not None:
        return hkml_view.cli_any_input(
                'Generating mails list again failed (%s).' % err)
    hkml_view.shell_mode_end(slist)
    slist.data = {'mail_idx_key_map': mail_idx_key_map,
                  'mails_effects': display_rule,
                  'collapsed_mails': {},
                  'data_generator': data_generator,
                  }
    slist.lines = text.split('\n')
    slist.screen.clear()
    hkml_view.shell_mode_start(slist)

def menu_export_mails(mail_slist, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    export_mails(None, slist)
    hkml_view.shell_mode_start(slist)

def menu_save_as(mail_slist, selection):
    mail, slist = mail_slist
    hkml_view.save_as('\n'.join(slist.lines))

def show_mails_list_menu(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return

    q = hkml_view.CliQuestion(
            desc='selected mail: %s' % mail.subject,
            prompt='Enter menu item number')
    hkml_view.shell_mode_start(slist)
    q.ask_selection(
            data=[mail, slist],
            selections=[
                hkml_view.CliSelection('open', menu_open_mail),
                hkml_view.CliSelection(
                    'list complete thread', menu_list_thread),
                hkml_view.CliSelection(
                    'collapse/expand focused thread', menu_collapse_expand),
                hkml_view.CliSelection(
                    'set display effects', menu_effect_mails),
                hkml_view.CliSelection('reply', menu_reply_mail),
                hkml_view.CliSelection('forward', menu_forward_mail),
                hkml_view.CliSelection(
                    'continue draft writing', menu_write_draft),
                hkml_view.CliSelection('manage tags', menu_manage_tags),
                hkml_view.CliSelection(
                    'handle as patches', menu_handle_patches),
                hkml_view.CliSelection(
                    'refresh', menu_refresh_mails),
                hkml_view.CliSelection(
                    'export as an mbox file', menu_export_mails),
                hkml_view.CliSelection(
                    'save screen content as ...', menu_save_as),
                ])
    hkml_view.shell_mode_end(slist)

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
            hkml_view.InputHandler(
                ['c'], collapse_focused_thread, 'collapse focused thread'),
            hkml_view.InputHandler(
                ['e'], expand_focused_thread, 'expand focused thread'),
            hkml_view.InputHandler(
                ['m'], show_mails_list_menu, 'open menu'),
            ]

def after_input_handle_callback(slist):
    mail_idx_key_map = slist.data['mail_idx_key_map']
    if mail_idx_key_map is None:
        return
    _, last_mail_idx_key_map = hkml_list.get_last_mails_list()
    if mail_idx_key_map != last_mail_idx_key_map:
        hkml_list.cache_list_str(
                'thread_output', '\n'.join(slist.lines), mail_idx_key_map)

def mails_display_effect_callback(slist, line_idx):
    if not 'mails_effects' in slist.data or slist.data['mails_effects'] is None:
        return slist.effect_normal
    mail, err = get_mail_of_row(slist, line_idx)
    if err is not None:
        return slist.effect_normal
    mail_display_effect = slist.data['mails_effects']
    if mail_display_effect.eligible(mail):
        return mail_display_effect.effect
    return slist.effect_normal

def show_mails_list(screen, text_lines, mail_idx_key_map, display_rule,
                    data_generator=None):
    slist = hkml_view.ScrollableList(screen, text_lines,
                           get_mails_list_input_handlers())
    slist.data = {'mail_idx_key_map': mail_idx_key_map,
                  'mails_effects': display_rule,
                  'collapsed_mails': {},
                  'data_generator': data_generator,
                  }
    slist.after_input_handle_callback = after_input_handle_callback
    slist.display_effect_callback = mails_display_effect_callback
    slist.draw()
    return slist

def gen_show_mails_list(screen, data_generator):
    hkml_view.shell_mode_start(screen)
    text, mail_idx_key_map, display_rule, err = data_generator.generate()
    if err is not None:
        return hkml_view.cli_any_input(
                'Failed mails list generating (%s).' % err)
    hkml_view.shell_mode_end(screen)

    return show_mails_list(screen, text.split('\n'), mail_idx_key_map,
                           display_rule, data_generator)

class MailsListDataGenerator:
    fn = None
    args = None

    def __init__(self, fn, args):
        self.fn = fn
        self.args = args

    def generate(self):
        # returns text, mail_idx_key_map, display_effect_rule, and error
        text, mail_idx_key_map, err = self.fn(self.args)
        if self.args.dim_old is None:
            return text, mail_idx_key_map, None, err

        display_effect_rule = MailDisplayEffect(interactive=False)
        display_effect_rule.effect = hkml_view.ScrollableList.effect_dim
        display_effect_rule.min_date = 'min'
        max_date_str = ' '.join(self.args.dim_old)
        for separator in ['-', ':']:
            max_date_str.replace(separator, ' ')
        try:
            display_effect_rule.max_date = datetime.datetime(
                    *[int(x) for x in max_date_str.split()]).astimezone()
        except Exception as e:
            err = 'wrong --dim_old (%s)' % self.args.dim_old
        return text, mail_idx_key_map, display_effect_rule, err
