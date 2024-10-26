# SPDX-License-Identifier: GPL-2.0

import datetime

def parse_date(date_str):
    for s in ['-', ':', '/']:
        date_str = date_str.replace(s, ' ')
    fields = date_str.split()
    if not len(fields) in [5, 3, 2]:
        return None, 'unexpected number of fields (%d)' % len(fields)
    if fields[0] == 'yesterday' and len(fields) == 3:
        now = datetime.datetime.now().astimezone()
        yesterday = now - datetime.timedelta(1)
        fields = [yesterday.year, yesterday.month, yesterday.day,
                  fields[1], fields[2]]
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
