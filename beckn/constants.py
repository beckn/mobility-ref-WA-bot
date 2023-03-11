from enum import IntEnum


class Action(IntEnum):

    def __new__(cls, value, action, callback=''):

        obj = int.__new__(cls, value)
        obj._value_ = value

        obj._action_name_ = action
        obj._callback_ = callback
        return obj

    @property
    def action_name(self):
        return self._action_name_

    @property
    def callback(self):
        return self._callback_

    SEARCH = 1, 'search', 'on_search'
    SELECT = 2, 'select', 'on_select'
    INIT = 3, 'init', 'on_init'
    CONFIRM = 4, 'confirm', 'on_confirm'
    STATUS = 5, 'status', 'on_status'
    TRACK = 6, 'track', 'on_track'
    UPDATE = 7, 'update', 'on_update'
    CANCEL = -1, 'cancel', 'on_cancel'
    SUPPORT = 8, 'support', 'on_support'

    @classmethod
    def list(cls):
        return list(map(lambda c: c.action_name, cls))


class BecknConstants:
    ACTION = Action
    ACK = 'ACK'
    NACK = 'NACK'
    KEY_MEDIATOR = ' | '
    BAP = 'BAP'
    BPP = 'BPP'
    GW  = 'GW'

