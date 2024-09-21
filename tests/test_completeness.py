import logging
from unittest import TestCase

from examples.gumball_machine import *
from lean import (
    StateMachine, State, StateException, TransitionException,
    StateMachineException)

import pytest


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SMWithoutInitialState(StateMachine):
    state_a1 = State('state_a1')
    state_a2 = State('state_a2', final=True)


class TestMissingInitialState(TestCase):
    def test_missing_initial_states(self):
        with pytest.raises(StateException):
            SMWithoutInitialState(name="Machina sin Nombre")


######################################################################


class SMWithoutFinalState(StateMachine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    state_a1 = State('state_a1', initial=True)
    state_a2 = State('state_a2')


class TestMissingFinalState(TestCase):
    def test_missing_final_state(self):
        with pytest.raises(StateException):
            SMWithoutFinalState(name="Machina sin Nombre")


######################################################################


class SMWithPluralInitialStates(StateMachine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    state_a1 = State('state_a', initial=True)
    state_a2 = State('state_a2', initial=True)


class TestPluralInitials(TestCase):
    def test_plural_initial_states(self):
        with pytest.raises(StateException):
            SMWithPluralInitialStates(name="Machina sin Nombre")


######################################################################


class SMWithoutTransitions(StateMachine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    state_a1 = State('state_a1', initial=True)
    state_a2 = State('state_a2', final=True)

class TestAbnormalMachines(TestCase):
    def test_machine_without_transitions(self):
        with pytest.raises(TransitionException) as exc:
            SMWithoutTransitions(name="Machina sin Nombre")
        assert "No transitions defined" in str(exc.value)


######################################################################


class SMWithoutSuperInit(StateMachine):
    def __init__(self, *args, **kwargs):
        pass

    state_a1 = State('state_a1', initial=True)
    state_a2 = State('state_a2', final=True)
    trans1 = state_a1.to(state_a2, cond="is_state_a1_to_a2")

    def is_state_a1_to_a2(self):
        return True


class TestMachineWithoutInitialState(TestCase):
    def test_machine_without_initial_state(self):
        with pytest.raises(AttributeError) as exc:
            sm = SMWithoutSuperInit(name="Machina sin Nombre")
            sm.cycle()
        assert "object has no attribute '_first_run'" in str(exc.value)


######################################################################


class SMWithoutTransitionCondition(StateMachine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    state_a1 = State('state_a1', initial=True)
    state_a2 = State('state_a2', final=True)
    trans1 = state_a1.to(state_a2)


class TestMachineWithoutTransCond(TestCase):
    def test_machine_without_transition_condition(self):
        with pytest.raises(TransitionException) as exc:
            sm = SMWithoutTransitionCondition(name="Machina sin Nombre")
            sm.cycle()
        assert "Transition trans1 has no 'cond' param," in str(exc.value)


######################################################################


class SMWithoutTransitionConditionImpl(StateMachine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    state_a1 = State('state_a1', initial=True)
    state_a2 = State('state_a2', final=True)
    trans1 = state_a1.to(state_a2, cond="is_state_a1_to_a2")


class TestMachineWithoutTransCondImpl(TestCase):
    def test_machine_without_transition_condition_impl(self):
        with pytest.raises(TransitionException) as exc:
            sm = SMWithoutTransitionConditionImpl(name="Machina sin Nombre")
            sm.cycle()
        assert "Transition trans1 has no 'cond' param," in str(exc.value)


######################################################################


class NormalStateMachine(StateMachine):
    state_a1 = State('state_a1', initial=True)
    state_a2 = State('state_a2')
    state_a3 = State('state_a3', final=True)

    state_a1_to_a2 = state_a1.to(state_a2, cond="is_state_a1_to_a2")
    state_a2_to_a3 = state_a2.to(state_a3, cond="should_state_a2_to_a3")

    def is_state_a1_to_a2(self, trans):
        return True

    def should_state_a2_to_a3(self, trans):
        return True


class TestNormalMachine(TestCase):
    def test_normal_machine(self):
        did_fail = False
        try:
            sm = NormalStateMachine(model=None, name="Machine com nombre")
            self.assertEqual(sm.state, NormalStateMachine.state_a1)
            sm.cycle()
            self.assertEqual(sm.state, NormalStateMachine.state_a2)
            sm.cycle()
            self.assertEqual(sm.state, NormalStateMachine.state_a3)
        except Exception as e:
            did_fail = True
        self.assertFalse(did_fail)


######################################################################


ALL_EXPECTED_EVENTS = [
    "is_state_a1_to_a2",
    "before_state_a1_to_a2",
    "on_exit_state_a1",
    "on_state_a1_to_a2",
    "after_state_a1_to_a2",
    "on_enter_state_a2",
    "should_state_a2_to_a3",
    "before_state_a2_to_a3",
    "on_exit_state_a2",
    "on_state_a2_to_a3",
    "after_state_a2_to_a3",
    "on_enter_state_a3",
]

class NormalStateMachineWithAllEvents(StateMachine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._events_called = list()

    state_a1 = State('state_a1', initial=True)
    state_a2 = State('state_a2')
    state_a3 = State('state_a3', final=True)

    state_a1_to_a2 = state_a1.to(state_a2, cond="is_state_a1_to_a2")
    state_a2_to_a3 = state_a2.to(state_a3, cond="should_state_a2_to_a3")

    """
    Every event callback is implemented, and every callback logs its name in
    order.  This enables testing that all callbacks were called, and called 
    in the correct order.
    """
    def on_enter_state_a1(self, event):
        """
        TODO: this never fires, because there is no transition to state_a1
        which mewans that a mechanism is needed to trigger first states
        """
        self._events_called.append('on_enter_state_a1')

    def is_state_a1_to_a2(self, event):
        self._events_called.append('is_state_a1_to_a2')
        return True

    def should_state_a2_to_a3(self, event):
        self._events_called.append('should_state_a2_to_a3')
        return True

    def before_state_a1_to_a2(self, event):
        self._events_called.append('before_state_a1_to_a2')

    def on_state_a1_to_a2(self, event):
        self._events_called.append('on_state_a1_to_a2')

    def on_exit_state_a1(self, event):
        self._events_called.append('on_exit_state_a1')

    def on_enter_state_a2(self, event):
        self._events_called.append('on_enter_state_a2')

    def after_state_a1_to_a2(self, event):
        self._events_called.append('after_state_a1_to_a2')

    def before_state_a2_to_a3(self, event):
        self._events_called.append('before_state_a2_to_a3')

    def on_exit_state_a2(self, event):
        self._events_called.append('on_exit_state_a2')

    def on_state_a2_to_a3(self, event):
        self._events_called.append('on_state_a2_to_a3')

    def on_enter_state_a3(self, event):
        self._events_called.append('on_enter_state_a3')

    def after_state_a2_to_a3(self, event):
        self._events_called.append('after_state_a2_to_a3')


class TestNormalMachineWithAllEvents(TestCase):
    def test_machine_with_all_event_callbacks_implemented(self):
        did_fail = False
        sm = NormalStateMachineWithAllEvents(name="Complete machine")
        try:
            self.assertEqual(sm.state,
                             NormalStateMachineWithAllEvents.state_a1)
            sm.cycle()
            self.assertEqual(sm.state,
                             NormalStateMachineWithAllEvents.state_a2)
            sm.cycle()
            self.assertEqual(sm.state,
                             NormalStateMachineWithAllEvents.state_a3)
        except Exception as e:
            # As a general check... this shouldn't be reached
            did_fail = True

        self.assertFalse(did_fail)

        # order doesn't matter with set subtraction
        self.assertEqual(set(sm._events_called) - set(ALL_EXPECTED_EVENTS), set())

        # order matters when comparing as lists
        for idx, event in enumerate(ALL_EXPECTED_EVENTS):
            self.assertEqual(sm._events_called[idx], event)


######################################################################


class TestGumballStateMachine(TestCase):
    def setUp(self):
        # Get a gumball machine hardware API
        self.gumball_hw = GumballMachineHardware()

        # Create a gumball machine state machine with the hardware API as context
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
        self.gumball_hw.coin_slot(COIN_DROP)

        # Cycle the state machine, which causes it to check the hardware API's new state
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
