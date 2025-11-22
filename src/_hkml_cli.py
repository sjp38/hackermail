# SPDX-License-Identifier: GPL-2.0

import os

import _hkml_fmtstr

'''
object for Question.ask_selection()
'text' is displayed to the user with the selection question.
'handle_fn' of user-selected one is called if it is not None.  The function
    receives user-set Question.data, user-entered input (number), and the
    selected Selection object.
'data' can save any selection-specific data.
'''
class Selection:
    text = None
    handle_fn = None    # function receiving question data, answer, selection
    data = None         # for carrying selection-specific data

    def __init__(self, text, handle_fn=None, data=None):
        self.text = text
        self.handle_fn = handle_fn
        self.data = data

'''
question that will be provided to the user, in shell mode.
ask_input() and ask_selection() are the methods that user will really use.
'''
class Question:
    description = None
    prompt = None
    allow_cancel = None

    def __init__(self, prompt=None, desc=None, allow_cancel=True):
        self.description = desc
        self.prompt = prompt
        self.allow_cancel = allow_cancel

    '''
    internal method.  Shouldn't be called directly from Question user.
    '''
    def ask(self, data, selections, handle_fn, notify_completion,
            default_selection=None):
        # return answer, selection, and error
        lines = ['']
        nr_cols = os.get_terminal_size().columns * 9 / 10
        if self.description is not None:
            for line in self.description.split('\n'):
                lines += _hkml_fmtstr.wrap_line(
                        prefix=None, line=line, nr_cols=nr_cols)
            lines.append('')
        if selections is not None:
            for idx, selection in enumerate(selections):
                line = selection.text
                if selection == default_selection:
                    line += ' (default)'
                lines += _hkml_fmtstr.wrap_line(
                        prefix='%d: ' % (idx + 1), line=line, nr_cols=nr_cols)
            lines.append('')
        if len(lines) > 0:
            print('\n'.join(lines))

        allow_cancel = self.allow_cancel

        enter_info = []
        if default_selection is not None:
            enter_info.append("'' for default option")
            if allow_cancel:
                enter_info.append("'cancel' to cancel")
        else:
            enter_info.append("'' to cancel)")
        prompt = '%s (%s): ' % (self.prompt, ', '.join(enter_info))

        answer = input(prompt)

        if allow_cancel is True:
            if default_selection is None:
                cancel_keyword = ''
            else:
                cancel_keyword = 'cancel'
            if answer == cancel_keyword:
                return None, None, 'canceled'

        selection = None
        selection_handle_fn = None
        if selections is not None:
            try:
                selection = selections[int(answer) - 1]
                selection_handle_fn = selection.handle_fn
            except:
                if answer == '' and default_selection is not None:
                    print('The default (%s) is selected.' %
                          default_selection.text)
                    selection = default_selection
                    selection_handle_fn = default_selection.handle_fn
                else:
                    return None, None, 'wrong input'

        if selection_handle_fn is not None:
            err = selection_handle_fn(data, answer, selection)
        elif handle_fn is not None:
            err = handle_fn(data, answer)
            if err:
                return None, None, err

        if notify_completion:
            print('Done.')
        return answer, selection, None

    '''
    Ask user to answer any text input.  If handle_fn is not None, the function
    is called with 'data' and user's input to the question.

    Should be invoked in shell mode (show shell_mode_start() and
    shell_mode_end()).

    Returns user's input to the question and error.
    '''
    def ask_input(self, data=None, handle_fn=None, notify_completion=False):
        answer, selection, err = self.ask(data, None, handle_fn,
                                          notify_completion)
        return answer, err

    '''
    Ask user to select on of Selection objects.  If the selected
    Selection has handle_fn field set, it is invoked.

    Should be invoked in shell mode (show shell_mode_start() and
    shell_mode_end()).

    Returns user's input to the question, selected Selection, and error.
    '''
    def ask_selection(self, selections, data=None, notify_completion=False,
                      default_selection=None):
        if self.prompt is None:
            self.prompt = 'Enter the item number'
        return self.ask(data, selections, None, notify_completion,
                        default_selection)

def ask_input(desc=None, prompt=None, handler_data=None,
              handle_fn=None):
    '''
    Prints 'desc', a blank line, and 'prompt'.  Then, wait for user input.  For
    given input, 'handle_fn' is called with 'handler_data' and the user input.

    Returns user's input to the question and an error.
    '''
    return Question(desc=desc, prompt=prompt).ask_input(
            data=handler_data, handle_fn=handle_fn)

def ask_selection(desc=None, selections_txt=None, selections=None, prompt=None,
                  handler_common_data=None,
                  allow_cancel=True, allow_error=True,
                  default_selection_idx=None):
    '''
    Prints 'desc', a blank line, 'selections', and 'prompt'.  Then, wait for
    user selection.  For given user input, 'handle_fn' of the selected
    'Selection' object is called with 'handler_common_data', the user input and
    the selected 'Selection' object.  Note that each 'Selection' object can
    have its own data for slection-specific one.

    Returns user's input to the question, the 'Selection' object, and an error.

    If selections is a list of strings, the second return value is not
    'Selection' object but the index of the selection on the list.
    '''
    if selections_txt is not None:
        selections = selections_txt
    string_selections = False
    if type(selections[0]) is str:
        string_selections = True
        selections = [Selection(s) for s in selections]
    default_selection = None
    if default_selection_idx is not None:
        default_selection = selections[default_selection_idx]

    while True:
        answer, selection, err = Question(
                desc=desc, prompt=prompt,
                allow_cancel=allow_cancel).ask_selection(
                        selections=selections, data=handler_common_data,
                        default_selection=default_selection)
        if allow_error is False and err is not None:
            print('Error (%s)' % err)
            print('Please answer correctly.')
            continue
        break

    if string_selections == False:
        return answer, selection, err
    selection = selections.index(selection)
    return answer, selection, err

yes_answers = ['y', 'yes']
no_answers = ['n', 'no']

def ask_yes_no(question=None, default_answer=None):
    if default_answer is None:
        question += ' [y/n] '
    elif default_answer == 'y':
        question += ' [Y/n] '
    elif default_answer == 'n':
        question += ' [y/N] '
    else:
        raise Exception('wrong default_answer: %s' % default_answer)
    while True:
        answer = input(question).lower()
        if default_answer == 'y':
            if not answer in no_answers:
                return 'y'
            else:
                return 'n'
        elif default_answer == 'n':
            if not answer in yes_answers:
                return 'n'
            else:
                return 'y'
        elif default_answer is None:
            if answer in yes_answers:
                return 'y'
            elif answer in no_answers:
                return 'n'
            continue
