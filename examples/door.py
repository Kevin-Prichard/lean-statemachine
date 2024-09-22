import logging
from enum import Enum

from box import Box

from lean import (StateMachine, State)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DoorPosition(Enum):
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'
    LOCKED = 'LOCKED'


class DoorHardware:
    def __init__(self):
        self._position = DoorPosition.CLOSED

    def is_closed(self):
        return self._position == DoorPosition.CLOSED

    def is_open(self):
        return self._position == DoorPosition.OPEN

    def is_locked(self):
        return self._position == DoorPosition.LOCKED

    def close(self):
        self._position = DoorPosition.CLOSED

    def open(self):
        self._position = DoorPosition.OPEN

    def lock(self):
        self._position = DoorPosition.LOCKED

    def unlock(self):
        self._position = DoorPosition.CLOSED


class Door(StateMachine):
    def __init__(self, door: DoorHardware, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hardware = door

    open = State('open', initial=True)
    closed = State('closed')
    locked = State('locked')

    closing = open.to(closed, 'close the door', cond='is_closed')
    opening = closed.to(open, 'open the door', cond='is_open')
    locking = closed.to(locked, 'lock the door', cond='is_locked')
    unlocking = locked.to(closed, 'unlock the door', cond='is_unlocked')

    def is_closed(self, event):
        return self._hardware.is_closed()

    def is_open(self, event):
        return self._hardware.is_open()

    def is_locked(self, event):
        return self._hardware.is_locked()

    def is_unlocked(self, event):
        return not self._hardware.is_locked()

    def on_closing(self):
        self._hardware.close()

    def on_opening(self):
        self._hardware.open()

    def on_locking(self):
        self._hardware.lock()

    def on_unlocking(self):
        self._hardware.unlock()
