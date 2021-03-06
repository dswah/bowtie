# -*- coding: utf-8 -*-
"""
Bowtie Component classes, all visual and control components inherit these
"""

import json
from datetime import datetime, time

import flask
from flask_socketio import emit
from future.utils import with_metaclass
from eventlet.event import Event
from eventlet.queue import LightQueue

from bowtie._compat import IS_PY35


def json_conversion(obj):

    if isinstance(obj, datetime) or isinstance(obj, time):
        return obj.isoformat()
    raise TypeError('Not sure how to serialize {} of type {}'.format(obj, type(obj)))


def jdumps(data):
    return json.dumps(data, default=json_conversion)


def make_event(event):

    @property
    def actualevent(self):
        name = event.__name__[3:]
        return '{uuid}#{event}'.format(uuid=self._uuid, event=name)

    if IS_PY35:
        # can't set docstring on properties in python 2 like this
        actualevent.__doc__ = event.__doc__

    return actualevent


def is_event(attribute):
    return attribute.startswith('on_')


def make_command(command):

    def actualcommand(self, data):
        name = command.__name__[3:]
        signal = '{uuid}#{event}'.format(uuid=self._uuid, event=name)
        if flask.has_request_context():
            return emit(signal, jdumps(data))
        else:
            sio = flask.current_app.extensions['socketio']
            return sio.emit(signal, jdumps(data))

    actualcommand.__doc__ = command.__doc__

    return actualcommand


def is_command(attribute):
    return attribute.startswith('do_')

class _Maker(type):
    def __new__(cls, name, parents, dct):
        for k in dct:
            if is_event(k):
                dct[k] = make_event(dct[k])
            if is_command(k):
                dct[k] = make_command(dct[k])
        return super(_Maker, cls).__new__(cls, name, parents, dct)


class Component(with_metaclass(_Maker, object)):
    _NEXT_UUID = 0

    @classmethod
    def _next_uuid(cls):
        cls._NEXT_UUID += 1
        return cls._NEXT_UUID

    def __init__(self):
        # wanted to put "self" instead of "Component"
        # was surprised that didn't work
        self._uuid = Component._next_uuid()
        super(Component, self).__init__()

    def get(self, block=True, timeout=None):
        event = LightQueue(1)
        if flask.has_request_context():
            emit('{}#get'.format(self._uuid), callback=lambda x: event.put(x))
        else:
            sio = flask.current_app.extensions['socketio']
            sio.emit('{}#get'.format(self._uuid), callback=lambda x: event.put(x))
        return event.get(timeout=1)
