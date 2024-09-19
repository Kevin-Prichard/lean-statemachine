import logging

from box import Box

from lean import (
    StateMachine, State, StateException, TransitionException,
    StateMachineException)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


COIN_DROP = "coin_inserted"

class GumballMachineHardware:
    def __init__(self):
        self._hardware = Box(
            coin_slot=False,
            speaker_play=lambda filename: logger.info("Speaker plays %s", filename),
            crank_position=0,
            leds=lambda *args: logger.info("LEDs play: %s", str(args))

        )

    def coin_slot(self, action):
        if action == "read":
            return self._hardware.coin_slot
        else:
            self._hardware.coin_slot = action

    def leds(self, action, color):
        self._hardware.leds(action, color)

    def is_crank_turning(self):
        return self._hardware.crank_position != 0

    def turn_crank(self, degrees):
        self._hardware.crank_position = degrees

    def gumball_dispensed(self):
        return self._hardware.crank_position == 0

    def sound_play(self, sound_file):
        self._hardware.speaker_play(sound_file)


class GumballStateMachine(StateMachine):
    ready = State('ready', initial=True,
                  desc='The machine is at rest and ready to begin a '
                       'purchase cycle')
    coin_dropped = State('coin_dropped',
                         'A coin has been inserted into the machine')
    crank_turned = State('crank_turned',
                         'The crank has been turned, and the '
                         'machine is '
                         'moving a gumball into the dispenser slot')
    gumball_dispensed = State('gumball_dispensed',
                              'A gumball has been dispensed to the customer')
    crank_returned = State('crank_returned', final=True,
                           desc='The crank has been returned to its original '
                                'position')

    paying = ready.to(
        coin_dropped, cond='is_coin_inserted',
        desc='A coin has been inserted into the machine')
    cranking = coin_dropped.to(
        crank_turned, cond='is_crank_turning',
        desc='The crank has been turned')
    dispensing = crank_turned.to(
        gumball_dispensed, cond='was_gumball_dispensed',
        desc='A gumball has been dispensed')
    finishing = gumball_dispensed.to(
        crank_returned, cond='on_crank_returned',
        desc='The crank has been returned to its original position')

    def is_coin_inserted(self, event):
        return self._model.coin_slot("read") == COIN_DROP

    def on_paying(self, event):
        logger.info("Coin being inserted")
        self._model.leds("blink", "green")
        self._model.sound_play("coin_inserted")

    def is_crank_turning(self, event):
        return self._model.crank("position") != 0

    def on_dispensing(self, event):
        self._model.finished

    def was_gumball_dispensed(self, event):
        return self._model.gumball_dispensed()

    def on_crank_returned(self, event):
        logger.info("Crank turning")
        self._model.leds("blink", "green")
        self._model.sound_play("crank_turned")
