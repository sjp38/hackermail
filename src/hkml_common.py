# SPDX-License-Identifier: GPL-2.0

import datetime
import subprocess

def parse_date(date_str):
    for s in ['-', ':', '/']:
        date_str = date_str.replace(s, ' ')
    fields = date_str.split()
    if not len(fields) in [5, 3, 2, 1]:
        return None, 'unexpected number of fields (%d)' % len(fields)
    if fields[0] == 'yesterday':
        now = datetime.datetime.now().astimezone()
        yesterday = now - datetime.timedelta(1)
        fields = [yesterday.year, yesterday.month, yesterday.day] + fields[1:]
    try:
        numbers = [int(x) for x in fields]
    except ValueError as e:
        return None, '%s' % e
    if not len(numbers) in [5, 3, 2]:
        # 5: year month day hour minute
        # 3: year month day
        # 2: hour minute
        return None, 'only 5, 3, or 2 numbers are supported date input'
    if len(numbers) == 2:
        now = datetime.datetime.now().astimezone()
        numbers = [now.year, now.month, now.day] + numbers
    try:
        return datetime.datetime(*numbers).astimezone(), None
    except Exception as e:
        return None, '%s' % e

def commit_date(commit):
    try:
        text = subprocess.check_output(
                ['git', 'log', '-1', commit, '--pretty=%cd',
                 '--date=iso-strict']).decode().strip()
    except Exception as e:
        return None, 'git log %s fail (%s)' % (commit, e)
    try:
        return datetime.datetime.fromisoformat(text).astimezone(), None
    except Exception as e:
        return None, 'parsing date (%s) fail (%s)' % (text, e)

def parse_date_arg_non_commit(tokens):
    try:
        date_str = ' '.join(tokens)
    except Exception as e:
        return None, 'tokens to string conversion fail (%s)' % e
    return parse_date(date_str)

def parse_date_arg(tokens):
    parsed, err = parse_date_arg_non_commit(tokens)
    if err is None:
        return parsed, err
    if len(tokens) != 1:
        return parsed, err
    parsed, err2 = commit_date(tokens[0])
    if err2 != None:
        err = 'parsing date argument fail (%s, %s)' % (err2, err)
    else:
        err = None
    return parsed, err

def date_format_description():
    return ' '.join([
        'Date arguments format is "YYYY MM DD HH MM".',
        '"-", "/", ":" on date input are treated as space.',
        '"YYYY MM DD" or "HH MM" also supported.',
        '\'yesterday\' can be used instead of "YYYY MM DD".'])

def add_date_arg(parser, option_name, help_msg):
    format_msg = date_format_description()
    if parser.epilog is None:
        parser.epilog = format_msg
    elif parser.epilog.find(format_msg) == -1:
        parser.epilog += format_msg
    help_msg += ' Format: show end of this message.'
    parser.add_argument(
            option_name, metavar='<date token>', nargs='+',
            help=help_msg)
