from asyncio import iscoroutine
from collections import defaultdict as dd
from functools import reduce, partial
import logging
from threading import Lock
from types import coroutine
from typing import List, Callable, Text, Union, Mapping, Any


GLOBAL_LOGGING_LEVEL=logging.INFO
logging.basicConfig(level=GLOBAL_LOGGING_LEVEL)
logger = logging.getLogger(__name__)

mutex = Lock()


class State(object):
    def __init__(self,
                 name: Text,
                 desc: Text = None,
                 initial: bool = False,
                 final: bool = False
                 ):
        self._name = name
        self._desc = desc
        self._initial = initial
        self._final = final

    def to(self,
           to_state: "State",
           name: Text = None,
           desc: Text = None,
           cond: Union[Text, Callable] = None
           ) -> "Transition":

        # to() is a convenience for attaching a Transition to a StateMachine
        return Transition(name=name, desc=desc,
                          state1=self, state2=to_state,
                          cond=cond)

    @property
    def name(self) -> Text:
        return self._name

    @property
    def initial(self) -> bool:
        return self._initial

    @property
    def final(self) -> bool:
        return self._final

    def __str__(self):
        return (f"State({self._name}: "
                f"initial={getattr(self, 'initial', None)}, "
                f"final={getattr(self, 'final', None)})")

    __repr__ = __str__


class Transition(object):
    """
    Transition between two states, qualified by a condition function
    There may be more than one next state, so it's up to your condition
    functions to determine which state will be next.

    :param name: Name of the transition
    :param state1: State from which the transition originates
    :param state2: State to which the transition goes
    :param cond: Condition under which the transition is valid
    """

    def __init__(self,
                 state1: State,
                 state2: State,
                 cond: Union[Text, Callable],
                 name: Text = None,
                 desc: Text = None
                 ):
        self._name = name
        self._state1 = state1
        self._state2 = state2
        self._desc = desc
        self._cond = cond

    @property
    def name(self) -> Text:
        return self._name

    @name.setter
    def name(self, name: Text):
        self._name = name

    @property
    def state1(self) -> State:
        return self._state1

    @property
    def state2(self) -> State:
        return self._state2

    @property
    def cond(self) -> Union[Text, Callable]:
        return self._cond

    def __str__(self) -> str:
        return (f"Transition({self._name}, "
                f"from:{self._state1}, "
                f"to:{self._state2}, "
                f"cond={self._cond}")

    __repr__ = __str__


class StateMachine(object):
    _transitions = dd(set)
    _initial_state = None

    def __init__(self,
                 name: Text,
                 desc: Text = None,
                 model: object = None,
                 *args, **kwargs):
        self._state = None
        self._name = name
        self._desc = desc
        self._model = model

        self._first_run = True
        try:
            # Perform once-only static initialization for the given subclass
            if mutex.acquire(blocking=True):
                klass = self.__class__
                if not klass.is_initialized:
                    klass.callbacks_init()
        finally:
            mutex.release()
        self._state = self._initial_state

    @classmethod
    @property
    def is_initialized(cls) -> bool:
        return getattr(cls, "_initial_state", None) is not None

    @property
    def state(self) -> State:
        return self._state

    @classmethod
    def callbacks_init(cls):
        # Build indexes for state and transition callbacks
        #
        # Note that we store the method function refs, not the bound methods.
        # This distinction is important, because multiple instances of the same
        # StateMachine subclass will share the same callback methods, and this
        # ensures that we always provide the correct instance passed as 'self'.
        cls._initial_state = None
        members = dir(cls)
        final_states = 0

        for name in filter(lambda n: not n.startswith('_'), members):
            attrib = getattr(cls, name)
            if isinstance(attrib, State):
                if attrib.initial:
                    if cls._initial_state:
                        raise StateException(
                            "Only one initial state per machine is permitted")
                    cls._initial_state = attrib
                if attrib.final:
                    final_states += 1
                if not attrib.name:
                    raise StateException("State must have a name")

            elif isinstance(attrib, Transition):
                if not attrib.name:
                    attrib.name = name
                if ((cond_name := getattr(attrib, 'cond')) is None or
                        getattr(cls, cond_name, None) is None):
                    raise TransitionException(
                        f"Transition {attrib.name} has no 'cond' param, or "
                        f"condition method "
                        f"'{cls.__name__}.{cond_name}' needs implementing")
                cls._transitions[attrib.state1].add(attrib)

                # Collect callbacks as partials, in proper firing order.
                # At runtime the 'self' param will be added to provide correct
                # context
                callbacks = []
                setattr(attrib, 'callbacks', callbacks)
                for event_type, actor in [("before", attrib),
                                          ("on_exit", attrib.state1),
                                          ("on", attrib),
                                          ("after", attrib),
                                          ("on_enter", attrib.state2)]:
                    if event_callback := getattr(
                            cls, f"{event_type}_{actor.name}", None):
                        callbacks.append(partial(event_callback, event=actor))

        if not cls._initial_state:
            raise StateException("One initial state must be defined")
        if not final_states:
            raise StateException("At least one final state must be defined")
        if not cls._transitions:
            raise TransitionException("No transitions defined")

    def cycle(self):
        klass = self.__class__

        if self._first_run:
            self._first_run = False
            if not getattr(self, '_state', None):
                raise StateMachineException(
                    "State machine has no current state. Did you forget to call "
                    "super().__init__(*args, **kwargs) from your own __init__ method?")

            if not klass._transitions:
                raise TransitionException(
                    "No transitions were found, or your StateMachine subclass "
                    "is not calling super().__init__(*args, **kwargs) from its "
                    "own __init__ method.")

        if self._state.final:
            return False

        # Get the transitions for the current state - there must be some,
        # unless the current state is marked final
        if not (candidates := klass._transitions.get(self._state, None)):
            raise TransitionException(
                f"No transitions found for state {self._state}")

        # Iterate the transitions from current state to other states
        # and check conditions
        for trans in candidates:
            if condition_fn := getattr(klass, trans.cond, None):
                if condition_fn(self, trans):
                    # Entered a transition with matching condition..
                    # Let's execute any defined callbacks. with 'self' as context
                    for callback in trans.callbacks:
                        callback(self=self)
                    self._state = trans.state2

                    # Transition complete - we do not look for other matching transitions
                    # If any exist, they were erroneous defined by the programmer
                    break

    def __getitem__(self, item: Text, something=None) -> Any:
        # if something is not None:
        #     import pudb; pu.db
        #     x = 12
        val = getattr(self, item, None)
        logger.debug("StateMachine.__getitem__(%s): %s", item,
                     str(val))
        if item.startswith("is_"):
            return item == f"is_{self._state.name}"
        return val

    def __str__(self) -> str:
        return f"StateMachine(state={self.state})"

    __repr__ = __str__


class TransitionException(Exception):
    pass

class StateException(Exception):
    pass

class StateMachineException(Exception):
    pass
