# SPDX-License-Identifier: GPL-2.0

import datetime

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

def main(args):
    print('wip')

def set_argparser(parser):
    pass
