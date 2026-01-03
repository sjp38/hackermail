# SPDX-License-Identifier: GPL-2.0

import datetime
import json
import os

import _hkml

class HistoryEvent:
    timestamp = None
    desc = None

    def __init__(self, timestamp, desc):
        self.timestamp = timestamp
        self.desc = desc

    def __str__(self):
        date = datetime.datetime.fromtimestamp(self.timestamp).astimezone()
        return '%s %s' % (date.strftime('%Y-%m-%d %H:%M:%S'), self.desc)

    @classmethod
    def from_kvpairs(cls, kvpairs):
        return cls(kvpairs['timestamp'], kvpairs['desc'])

    def to_kvpairs(self):
        return {
                'timestamp': self.timestamp,
                'desc': self.desc,
                }

class History:
    events = None

    def __init__(self, events):
        self.events = events

    @classmethod
    def from_kvpairs(cls, kvpairs):
        events = [HistoryEvent.from_kvpairs(kvp) for kvp in kvpairs['events']]
        return cls(events=events)

    def to_kvpairs(self):
        return {
                'events': [e.to_kvpairs() for e in self.events],
                }

history = None

def history_file_path():
    return os.path.join(_hkml.get_hkml_dir(), 'hkml_history')

def get_history():
    global history
    if history is not None:
        return history

    file_path = history_file_path()
    try:
        with open(file_path, 'r') as f:
            history_kvpairs = json.load(f)
    except:
        history = History(events=[])
        return history
    history = History.from_kvpairs(history_kvpairs)
    return history

def writeback_history():
    file_path = history_file_path()
    with open(file_path, 'w') as f:
        json.dump(history.to_kvpairs(), f, indent=4)

def add_event(desc):
    timestamp = datetime.datetime.now().timestamp()
    event = HistoryEvent(timestamp, desc)

    history = get_history()
    if len(history.events) >= 256:
        history.events = history.events[1:]
    history.events.append(event)
    writeback_history()

def main(args):
    if args.action == 'list':
        history = get_history()
        nr_events = args.nr_events
        if nr_events is None:
            nr_events = 10
        for event in history.events[-1 * nr_events:]:
            print('%s' % event)

def set_argparser(parser):
    parser.description = 'manage hkml usage history'

    subparsers = parser.add_subparsers(
            title='action', dest='action', metavar='<action>', required=True)
    parser_list = subparsers.add_parser('list', help='list previous history')
    parser_list.add_argument(
            '--nr_events', type=int, help='number of recent events to list')
