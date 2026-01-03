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

def main(args):
    print('wip')

def set_argparser(parser):
    pass
