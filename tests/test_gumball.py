from unittest import TestCase

from examples.gumball_machine import (
    COIN_SLOT_OCCUPIED, GumballMachineHardware, GumballStateMachine)


class TestGumballStateMachine(TestCase):
    def setUp(self):
        # Get a gumball machine hardware API
        self.gumball_hw = GumballMachineHardware()

        # Create a gumball machine state machine with hardware API as context
        self.gumball_sm = GumballStateMachine(
            name="Gumball state machine controller",
            desc="Demo of a gumball machine controlled by lean-statemachine",
            model=self.gumball_hw)

    def test_ready(self):
        self.assertEqual(self.gumball_sm.state,
                         GumballStateMachine.ready)

    def test_coin_insert(self):
        # the just-instantiated gumball machine should be in the ready state
        self.assertEqual(self.gumball_sm.state,
                         GumballStateMachine.ready)

        # Simulate the user dropping a coin, by telling the gumball hardware
        self.gumball_hw.coin_slot(COIN_SLOT_OCCUPIED)

        # Cycle the state machine, causing it to check hardware API's new state
        self.gumball_sm.cycle()

        # The
        self.assertEqual(self.gumball_sm.state,
                         GumballStateMachine.coin_dropped)

        # User turns the crank ...
        for degree in (90, 180, 270, 360):
            self.gumball_hw.turn_crank(degree)
            self.gumball_sm.cycle()

            # check that the gumball has NOT dropped
            if degree < 360:
                self.assertEqual(self.gumball_sm.state,
                                 GumballStateMachine.crank_turned)

        # When the crank has spun around 360 degrees, the gumball will drop
        self.assertEqual(self.gumball_sm.state,
                         GumballStateMachine.gumball_dispensed)

        self.gumball_sm.cycle()

        self.assertEqual(self.gumball_sm.state,
                         GumballStateMachine.crank_returned)

        # No further advancement possible as state 'crank_returned' is final,
        # so .cycle() will return False
        self.assertFalse(self.gumball_sm.cycle())


######################################################################
