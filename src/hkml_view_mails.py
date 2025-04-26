# SPDX-License-Identifier: GPL-2.0

import argparse
import curses
import datetime
import os

import _hkml_list_cache
import hkml_cache
import hkml_common
import hkml_export
import hkml_forward
import hkml_list
import hkml_open
import hkml_patch
import hkml_reply
import hkml_tag
import hkml_view
import hkml_view_text
import hkml_write

# mails list

def mail_of_row(slist, row):
    line_nr_mail_map = slist.data.list_data.line_nr_mail_map
    # in case of cached output reuse, the map is None
    if line_nr_mail_map is None:
        refresh_list(slist)
        line_nr_mail_map = slist.data.list_data.line_nr_mail_map
    row -= slist.data.list_data.len_comments
    if not row in line_nr_mail_map:
        return None
    return line_nr_mail_map[row]

def get_focused_mail(slist):
    return mail_of_row(slist, slist.focus_row)

def focused_mail_idx(slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return None
    return mail.pridx

def open_focused_mail(c, slist):
    mail = get_focused_mail(slist)
    if mail is None:
        return

    _, cols = slist.screen.getmaxyx()
    lines = hkml_open.mail_display_str(mail, cols).split('\n')

    cursor_position_cache = slist.data.last_cursor_position
    msgid = mail.get_field('message-id')
    if msgid in cursor_position_cache:
        cursor_position = cursor_position_cache[msgid]
    else:
        cursor_position = None

    text_view_data = hkml_view_text.TextViewData(mail, get_mails(slist))

    text_view_list = hkml_view_text.show_text_viewer(
            slist.screen, lines, data=text_view_data,
            cursor_position=cursor_position)
    cursor_position_cache[msgid] = [text_view_list.focus_row,
                                    text_view_list.focus_col]

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

def suggest_continuing_draft(drafts):
    if len(drafts) == 0:
        return None
    drafts = sorted(drafts, key=lambda d: d.date)
    answered = False
    print('you have drafts of subject "%s" written at below dates' %
          drafts[0].subject)
    print()
    for idx, draft_mail in enumerate(drafts):
        print('%d. %s' % (idx, draft_mail.date))
    print()
    while True:
        answer = input(' '.join(
            ['Continue writing the draft that written most recently?',
             '[Y/n/index of other draft] ']))
        if answer.lower() == 'n':
            return None
        if answer == '':
            answer = -1
        try:
            return drafts[int(answer)]
        except:
            print('wrong input...')
            pass
    return None

def reply_mail(slist, mail):
    hkml_view.shell_mode_start(slist)
    reply_subject = hkml_reply.format_reply_subject(mail)
    drafts = hkml_tag.get_mails_of_subject_tag(reply_subject, 'drafts')
    draft = suggest_continuing_draft(drafts)
    if draft is not None:
        hkml_write.write_send_mail(
                draft_mail=draft, subject=None, in_reply_to=None, to=None,
                cc=None, body=None, attach=None, format_only=None)
    else:
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

def hkml_list_args_for_msgid(msgid):
    parser = argparse.ArgumentParser()
    hkml_list.set_argparser(parser)
    return parser.parse_args([msgid])

def list_thread_of_focused_mail(c, slist):
    msgid = get_focused_mail(slist).get_field('message-id')
    args = hkml_list_args_for_msgid(msgid)
    gen_show_mails_list(slist.screen, args)

def refresh_list(slist):
    comment_lines = []
    for line in slist.lines:
        if line.startswith('#'):
            comment_lines.append(line)
    slist.data.list_data.len_comments = len(comment_lines)

    collapsed_mails = slist.data.collapsed_mails

    mails = get_mails(slist)
    decorator = hkml_list.MailListDecorator(None)
    decorator.collapse = False
    decorator.show_url = False
    _, cols = slist.screen.getmaxyx()
    decorator.cols = int(cols * 0.9)

    lines, line_nr_mail_map = hkml_list.fmt_mails_text(
            mails, decorator, collapsed_mails)
    slist.data.list_data.line_nr_mail_map = line_nr_mail_map
    text = '\n'.join(lines)
    slist.set_lines(comment_lines + text.split('\n'))
    slist.focus_row = min(slist.focus_row, len(slist.lines) - 1)
    slist.screen.clear()

def collapse_focused_thread(c, slist):
    collapsed_mails = slist.data.collapsed_mails

    collapsed_mails[focused_mail_idx(slist)] = True
    refresh_list(slist)

def expand_focused_thread(c, slist):
    collapsed_mails = slist.data.collapsed_mails
    del collapsed_mails[focused_mail_idx(slist)]
    refresh_list(slist)

def write_mail_draft(slist, mail):
    hkml_view.shell_mode_start(slist)
    hkml_write.write_send_mail(
            draft_mail=mail, subject=None, in_reply_to=None, to=None,
            cc=None, body=None, attach=None, format_only=None)
    hkml_view.shell_mode_end(slist)

def do_add_tags(data, answer, selection):
    mail, tags = data
    prompt = ' '.join(['Enter tags to add, separated by white spaces',
                       '(enter \'cancel_tag\' to cancel): '])
    tags = input(prompt).split()
    if 'cancel_tag' in tags:
        _ = input('Canceled.  Press enter to return')
        return 'canceled'
    hkml_tag.do_add_tags(mail, tags, None)

def do_remove_tags(data, answer, selection):
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
                hkml_view.CliSelection('Add tags', handle_fn=do_add_tags),
                hkml_view.CliSelection('Remove tags',
                                       handle_fn=do_remove_tags)])

def do_check_patch(data, answer, selection):
    mail = data
    err = hkml_patch.check_apply_or_export(mail, argparse.Namespace(
        hkml_dir=None, command='patch', dont_add_cv='ask', action='check',
        checker=None))
    if err is not None:
        print('applying action failed (%s)' % err)

def do_apply_patch(data, answer, selection):
    mail = data
    err = hkml_patch.check_apply_or_export(mail, argparse.Namespace(
        hkml_dir=None, command='patch', dont_add_cv=True, action='apply',
        repo='./'))
    if err is not None:
        print('applying action failed (%s)' % err)

def do_export_patch(data, answer, selection):
    export_dir, err = hkml_view.CliQuestion(
            'Enter relative directory to export patch files').ask_input()
    if err == 'canceled':
        return
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    elif not os.path.isdir(export_dir):
        print('%s exisits, and not a directory' % export_dir)
        return

    mail = data
    err = hkml_patch.check_apply_or_export(mail, argparse.Namespace(
        hkml_dir=None, command='patch', dont_add_cv='ask', action='export',
        repo='./', export_dir=export_dir))
    if err is not None:
        print('applying action failed (%s)' % err)

def handle_patches_of_mail(mail, list_mails=None):
    msgid = mail.get_field('message-id')
    if list_mails is None:
        list_mails, err = hkml_list.get_thread_mails_from_web(msgid)
        if err is not None:
            print('get_thread_mails_from_web() failed (%s)' % err)
            return
    threads = hkml_list.threads_of(list_mails)
    mail_with_replies = None
    for thread_root_mail in threads:
        mail_with_replies = hkml_patch.find_mail_from_thread(
                thread_root_mail, msgid)
        if mail_with_replies is not None:
            break
    if mail_with_replies is None:
        print('getting mail with replies failed.')
        return
    mail = mail_with_replies

    q = hkml_view.CliQuestion(
            desc='Handle the mail (\'%s\') as patch[es].' % mail.subject,
            prompt='Enter the item number')
    q.ask_selection(
            data=mail,
            selections=[
                hkml_view.CliSelection(
                    'check patch[es]', handle_fn=do_check_patch),
                hkml_view.CliSelection(
                    'apply patch[es]', handle_fn=do_apply_patch),
                hkml_view.CliSelection(
                    'export patch[es]', handle_fn=do_export_patch)],
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
    mail_idx_key_map = slist.data.list_data.mail_idx_key_map
    for mail_idx in mail_idx_key_map:
        mail_key = mail_idx_key_map[mail_idx]
        mail = hkml_cache.get_mail(key=mail_key)
        mail.pridx = int(mail_idx)
        mail.filtered_out = False
        mails.append(mail)
    set_prdepth(mails)
    return mails

def do_export(data, answer, selection):
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
                print(err)
                return err
            export_range[1] += 1    # export receives half-open range
        except:
            err = 'wrong input.'
            print(err)
            return err
    else:
        export_range = None

    answer = input('may I export those in human/chatbot-readable form? [y/N] ')
    human_readable = answer.lower() == 'y'

    file_name = hkml_view.receive_file_path(for_read=False)
    if file_name is None:
        return 'file unselected'
    mails = get_mails(slist)

    if export_range != None:
        filtered = [m for m in mails
                    if m.pridx >= export_range[0] and
                    m.pridx < export_range[1]]
        mails = filtered
    hkml_export.export_mails(mails, file_name, human_readable=human_readable)
    print()

def export_mails(c, slist):
    idx = focused_mail_idx(slist)
    hkml_view.shell_mode_start(slist)

    q = hkml_view.CliQuestion(desc='Focused mail: %d' % idx)
    q.ask_selection(
            data=[slist, idx],
            selections=[
                hkml_view.CliSelection(
                    'Export only focused mail', handle_fn=do_export),
                hkml_view.CliSelection(
                    'Export a range of mails of the list',
                    handle_fn=do_export),
                hkml_view.CliSelection(
                    'Export all mails of the list', handle_fn=do_export)],
                notify_completion=True)
    hkml_view.shell_mode_end(slist)

def menu_open_mail(mail_slist, answer, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    open_focused_mail(None, slist)
    hkml_view.shell_mode_start(slist)

def menu_list_thread(mail_slist, answer, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    list_thread_of_focused_mail(None, slist)
    hkml_view.shell_mode_start(slist)

def menu_collapse_expand(mail_slist, answer, selection):
    mail, slist = mail_slist
    if focused_mail_idx(slist) in slist.data.collapsed_mails:
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
    old_effect = None
    effect = None

    def eligible(self, mail):
        if self.min_date is not None:
            if self.min_date != 'min' and mail.date < self.min_date:
                return False
        if self.max_date is not None:
            if self.max_date != 'max' and mail.date > self.max_date:
                return False
        if self.effect is None:
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
        prompt = ' '.join(['Minimum date.',
                           hkml_common.date_format_description(),
                           '"min" keyword is also supported.'])
        q = hkml_view.CliQuestion(prompt=prompt)
        answer, err = q.ask_input()
        if err is not None:
            return
        if answer == 'min':
            self.min_date = answer
        else:
            self.min_date, err = hkml_common.parse_date(answer)
            if err is not None:
                print(err)
                return
        prompt = ' '.join(['Maximum date.',
                           hkml_common.date_format_description(),
                           '"max" keyword is also supported.'])
        q = hkml_view.CliQuestion(prompt=prompt)
        answer, err = q.ask_input()
        if err is not None:
            return
        if answer == 'max':
            self.max_date = answer
        else:
            self.max_date, err = hkml_common.parse_date(answer)
            if err is not None:
                print(err)
                return

    def __init__(self, interactive, old_effect=None):
        if interactive is False:
            return
        q = hkml_view.CliQuestion(
                desc='Select the display effect to apply.', prompt=None)

        def handle_selection(data, answer, selection):
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
            self.effect = old_effect
            return
        self.interactive_setup_dates()

def menu_effect_mails(mail_slist, answer, selection):
    print('Apply a display effect to specific mails.')
    print()
    mail, slist = mail_slist
    print('current display effect:')
    print('%s' % slist.data.display_rule)
    print()

    # In case the user cancels the effect selection, we want to be able
    # to restore their old settings.
    old_mail_display_effect = slist.data.display_rule
    if old_mail_display_effect is not None:
        old_effect = old_mail_display_effect.effect
    else:
        old_effect = None

    slist.data.display_rule = MailDisplayEffect(
            interactive=True, old_effect=old_effect)

def mk_dim_old_rule(max_date):
    effect_rule = MailDisplayEffect(interactive=False)
    effect_rule.effect = hkml_view.ScrollableList.effect_dim
    effect_rule.min_date = 'min'
    effect_rule.max_date = max_date
    return effect_rule

def build_suggest_dim_old_prompt(last_dates):
    lines = ['']
    now_time = datetime.datetime.now().astimezone()
    if len(last_dates) == 0:
        lines += [
                  'May I dim mails on the list that are older than a date?',
                  "- Enter the date to dim mails older than it (%s)." %
                  hkml_common.date_format_description(),
                  "- Or, enter 'n' if you don't want to dim any mail.",
                  ]
    else:
        lines.append('Dates you generated old versions of the list are:')
        for idx, last_date in enumerate(last_dates):
            lines.append(' %2d. %s (%s before)' %
                  (idx, last_date, now_time - last_date))
        lines += [
                '',
                'May I dim mails older than the latest one (%s)?' %
                last_dates[-1],
                "- Enter 'y' or nothing if yes.",
                "- Enter 'n' if you don't want to dim any mail.",
                "- Enter an index on the above list to select te date of it.",
                "- Or, enter custom date to dim mails older than it (%s)." %
                hkml_common.date_format_description(),
                ]
    lines += ['', 'Enter: ']
    return lines

def suggest_dim_old(key):
    last_dates = _hkml_list_cache.get_cache_creation_dates(key)
    # the very last created date is that for the current list.  Exclude it.
    last_dates = last_dates[:-1]
    answer = input('\n'.join(build_suggest_dim_old_prompt(last_dates)))
    answer_fields = answer.split()
    _, err = hkml_common.parse_date_arg(answer_fields)
    if err is None:
        return answer_fields
    if answer.lower() == 'n':
        return None
    if len(last_dates) == 0:
        print('The input is not a valid date.  Do not dim_old')
        return None
    try:
        the_date  = last_dates[int(answer)]
    except:
        if answer in ['', 'y']:
            the_date = last_dates[-1]
        else:
            print('Wrong input.  Do not dim_old')
            return None
    date_str = the_date.strftime('%Y-%m-%d %H:%M')
    print('\nThe list will dim mails older than %s' % date_str)
    return [date_str]

def menu_dim_old_mails(mail_slist, answer, selection):
    mail, slist = mail_slist
    gen_args = slist.data.list_args
    key = hkml_list.args_to_lists_cache_key(gen_args)
    max_date_str = suggest_dim_old(key)
    if max_date_str is None:
        return
    max_date, err = hkml_common.parse_date_arg(max_date_str)
    if err is not None:
        print(err)
        return

    slist.data.display_rule = mk_dim_old_rule(max_date)

def menu_reply_mail(mail_slist, answer, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    reply_focused_mail(None, slist)
    hkml_view.shell_mode_start(slist)

def menu_forward_mail(mail_slist, answer, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    forward_focused_mail(None, slist)
    hkml_view.shell_mode_start(slist)

def menu_write_draft(mail_slist, answer, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    write_mail_draft(slist, mail)
    hkml_view.shell_mode_start(slist)

def menu_manage_tags(mail_slist, answer, selection):
    mail, slist = mail_slist
    manage_tags_of_mail(slist, mail)

def menu_handle_patches(mail_slist, answer, selection):
    mail, slist = mail_slist
    handle_patches_of_mail(mail, get_mails(slist))

class MailsViewData:
    list_data = None
    list_args = None
    display_rule = None
    collapsed_mails = None
    last_cursor_position = None
    display_effects = None      # cache display effect per line

    def __init__(self, list_data, list_args, display_rule):
        self.list_data = list_data
        self.list_args = list_args
        self.display_rule = display_rule
        self.collapsed_mails = {}
        self.last_cursor_position = {}
        self.display_effects = {}

def menu_refresh_mails(mail_slist, answer, selection):
    mail, slist = mail_slist
    gen_args = slist.data.list_args
    if type(gen_args) is argparse.Namespace and gen_args.fetch is False:
        answer = input('"--fetch" is unset.  Set it? [Y/n] ')
        if answer.lower() != 'n':
            gen_args.fetch = True

    mails_view_data, err = generate_mails_view_data(gen_args)
    if err is not None:
        print('Generating mails list again failed (%s).' % err)
        return
    list_data = mails_view_data.list_data
    hkml_view.shell_mode_end(slist)
    slist.data = mails_view_data
    slist.set_lines(list_data.text.split('\n'))
    slist.screen.clear()
    hkml_view.shell_mode_start(slist)

def menu_search(mail_slist, answer, selection):
    _, slist = mail_slist
    answer, err = hkml_view.CliQuestion(
            desc='Search mails having keywords',
            prompt='Enter keywords').ask_input()
    if err is not None:
        return
    keywords = answer.split()
    searched_lines = []
    last_mail = None
    for row in range(0, len(slist.lines)):
        mail = mail_of_row(slist, row)
        if mail is None or mail == last_mail:
            continue
        body = mail.get_field('body')
        searched = True
        for keyword in keywords:
            if not keyword in body:
                searched = False
                continue
        if searched:
            searched_lines. append(row)
    slist.set_searched_lines(searched_lines)
    if len(searched_lines) > 0:
        hkml_view.ask_highlight_enabling(slist)
        slist.search_keyword = None

def menu_new_list(mail_slist, answer, selection):
    mail, slist = mail_slist
    answer, err = hkml_view.CliQuestion(
            desc='Open new list with different arguments',
            prompt=' '.join([
                "Enter 'hml list' command line arguments",
                'for the new list'])).ask_input()
    if err is not None:
        return
    parser = argparse.ArgumentParser()
    hkml_list.set_argparser(parser)
    try:
        args = parser.parse_args(answer.split())
    except Exception as e:
        print('parsing new option failed: %s' % e)
        return
    gen_show_mails_list(slist.screen, args)

def menu_export_mails(mail_slist, answer, selection):
    mail, slist = mail_slist
    hkml_view.shell_mode_end(slist)
    export_mails(None, slist)
    hkml_view.shell_mode_start(slist)

def menu_save_as(mail_slist, answer, selection):
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
                hkml_view.CliSelection('open', handle_fn=menu_open_mail),
                hkml_view.CliSelection(
                    'list complete thread', handle_fn=menu_list_thread),
                hkml_view.CliSelection(
                    'collapse/expand focused thread',
                    handle_fn=menu_collapse_expand),
                hkml_view.CliSelection(
                    'dim old mails', handle_fn=menu_dim_old_mails),
                hkml_view.CliSelection(
                    'set display effects', handle_fn=menu_effect_mails),
                hkml_view.CliSelection('reply', handle_fn=menu_reply_mail),
                hkml_view.CliSelection(
                    'forward', handle_fn=menu_forward_mail),
                hkml_view.CliSelection(
                    'continue draft writing', handle_fn=menu_write_draft),
                hkml_view.CliSelection(
                    'manage tags', handle_fn=menu_manage_tags),
                hkml_view.CliSelection(
                    'handle as patches', handle_fn=menu_handle_patches),
                hkml_view.CliSelection(
                    'refresh', handle_fn=menu_refresh_mails),
                hkml_view.CliSelection(
                    'search mails', handle_fn=menu_search),
                hkml_view.CliSelection(
                    'open new list', handle_fn=menu_new_list),
                hkml_view.CliSelection(
                    'export as an mbox file', handle_fn=menu_export_mails),
                hkml_view.CliSelection(
                    'save screen content to ...', handle_fn=menu_save_as),
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
    list_data = slist.data.list_data
    mail_idx_key_map = list_data.mail_idx_key_map
    if mail_idx_key_map is None:
        return
    _, last_mail_idx_key_map = _hkml_list_cache.get_last_mails_list()
    if mail_idx_key_map != last_mail_idx_key_map:
        _hkml_list_cache.set_item('thread_output', list_data)

def mails_display_effect_callback(slist, line_idx):
    display_effects_cache = slist.data.display_effects
    if line_idx in display_effects_cache:
        return display_effects_cache[line_idx]

    if slist.data.display_rule is None:
        return slist.effect_normal
    mail = mail_of_row(slist, line_idx)
    if mail is None:
        display_effects_cache[line_idx] = slist.effect_normal
        return slist.effect_normal
    mail_display_effect = slist.data.display_rule
    if mail_display_effect.eligible(mail):
        display_effects_cache[line_idx] = mail_display_effect.effect
        return mail_display_effect.effect
    display_effects_cache[line_idx] = slist.effect_normal
    return slist.effect_normal

def show_mails_list(screen, mails_view_data):
    list_data = mails_view_data.list_data
    display_rule = mails_view_data.display_rule
    list_args = mails_view_data.list_args
    text_lines = list_data.text.split('\n')
    slist = hkml_view.ScrollableList(screen, text_lines,
                           get_mails_list_input_handlers())
    slist.data = mails_view_data
    slist.after_input_handle_callback = after_input_handle_callback
    slist.display_effect_callback = mails_display_effect_callback
    if list_data.len_comments is not None:
        slist.focus_row = min(list_data.len_comments, len(text_lines) - 1)
    slist.draw()
    return slist

def generate_mails_view_data(args):
    # returns MailsViewData and error
    list_data, err = hkml_list.args_to_mails_list_data(args)
    if err is not None:
        return None, err
    if not hasattr(args, 'dim_old') or args.dim_old is None:
        args.dim_old = suggest_dim_old(
                hkml_list.args_to_lists_cache_key(args))
        if args.dim_old is None:
            return MailsViewData(list_data, args, None), err

    max_date, err = hkml_common.parse_date_arg(args.dim_old)
    if err is not None:
        err = 'wrong --dim_old (%s)' % err
        display_effect_rule = None
    else:
        display_effect_rule = mk_dim_old_rule(max_date)
    mails_view_data = MailsViewData(list_data, args, display_effect_rule)
    return mails_view_data, err

def gen_show_mails_list(screen, list_args):
    hkml_view.shell_mode_start(screen)

    mails_view_data, err = generate_mails_view_data(list_args)
    if err is not None:
        print('Failed mails list generating (%s).' % err)
    hkml_view.shell_mode_end(screen)

    if err is not None:
        return

    return show_mails_list(screen, mails_view_data)
