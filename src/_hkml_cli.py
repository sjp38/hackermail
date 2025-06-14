# SPDX-License-Identifier: GPL-2.0

"""
object for Question.ask_selection()
'text' is displayed to the user with the selection question.
'handle_fn' of user-selected one is called if it is not None.  The function
    receives user-set Question.data, user-entered input (number), and the
    selected Selection object.
'data' can save any selection-specific data.
"""


class Selection:
    text = None
    handle_fn = None  # function receiving question data, answer, selection
    data = None  # for carrying selection-specific data

    def __init__(self, text, handle_fn=None, data=None):
        self.text = text
        self.handle_fn = handle_fn
        self.data = data


"""
question that will be provided to the user, in shell mode.
ask_input() and ask_selection() are the methods that user will really use.
"""


class Question:
    description = None
    prompt = None

    def __init__(self, prompt=None, desc=None):
        self.description = desc
        self.prompt = prompt

    """
    internal method.  Shouldn't be called directly from Question user.
    """

    def ask(
        self, data, selections, handle_fn, notify_completion, default_selection=None
    ):
        # return answer, selection, and error
        lines = [""]
        if self.description is not None:
            lines.append(self.description)
            lines.append("")
        if selections is not None:
            for idx, selection in enumerate(selections):
                lines.append("%d: %s" % (idx + 1, selection.text))
            lines.append("")
        if len(lines) > 0:
            print("\n".join(lines))

        if default_selection is None:
            prompt = "%s (enter '' to cancel): " % self.prompt
        else:
            prompt = "%s (enter '' for '%s', 'cancel' to cancel): " % (
                self.prompt,
                default_selection.text,
            )

        answer = input(prompt)
        if answer == "":
            if default_selection is None:
                print("Canceled.")
                return None, None, "canceled"
            else:
                print("The default (%s) selected." % default_selection.text)
                return "", default_selection, None

        if answer == "cancel" and default_selection is not None:
            print("Canceled.")
            return None, None, "canceled"

        selection = None
        selection_handle_fn = None
        if selections is not None:
            try:
                selection = selections[int(answer) - 1]
                selection_handle_fn = selection.handle_fn
            except:
                print("Wrong input.")
                return None, None, "wrong input"

        if selection_handle_fn is not None:
            err = selection_handle_fn(data, answer, selection)
        elif handle_fn is not None:
            err = handle_fn(data, answer)
            if err:
                return None, None, err

        if notify_completion:
            print("Done.")
        return answer, selection, None

    """
    Ask user to answer any text input.  If handle_fn is not None, the function
    is called with 'data' and user's input to the question.

    Should be invoked in shell mode (show shell_mode_start() and
    shell_mode_end()).

    Returns user's input to the question and error.
    """

    def ask_input(self, data=None, handle_fn=None, notify_completion=False):
        answer, selection, err = self.ask(data, None, handle_fn, notify_completion)
        return answer, err

    """
    Ask user to select on of Selection objects.  If the selected
    Selection has handle_fn field set, it is invoked.

    Should be invoked in shell mode (show shell_mode_start() and
    shell_mode_end()).

    Returns user's input to the question, selected Selection, and error.
    """

    def ask_selection(
        self, selections, data=None, notify_completion=False, default_selection=None
    ):
        if self.prompt is None:
            self.prompt = "Enter the item number"
        return self.ask(data, selections, None, notify_completion, default_selection)


def ask_input(desc=None, prompt=None, handler_data=None, handle_fn=None):
    """
    Prints 'desc', a blank line, and 'prompt'.  Then, wait for user input.  For
    given input, 'handle_fn' is called with 'handler_data' and the user input.

    Returns user's input to the question and an error.
    """
    return Question(desc=desc, prompt=prompt).ask_input(
        data=handler_data, handle_fn=handle_fn
    )


def ask_selection(
    desc=None,
    selections=None,
    prompt=None,
    handler_common_data=None,
    default_selection=None,
):
    """
    Prints 'desc', a blank line, 'selections', and 'prompt'.  Then, wait for
    user selection.  For given user input, 'handle_fn' of the selected
    'Selection' object is called with 'handler_common_data', the user input and
    the selected 'Selection' object.  Note that each 'Selection' object can
    have its own data for slection-specific one.

    Returns user's input to the question, the 'Selection' object, and an error.
    """
    return Question(desc=desc, prompt=prompt).ask_selection(
        selections=selections,
        data=handler_common_data,
        default_selection=default_selection,
    )
