from collections import defaultdict as dd
from functools import partial
import logging
from threading import Lock
from typing import Callable, Text, Union, Any, Set


GLOBAL_LOGGING_LEVEL = logging.INFO
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
    def desc(self) -> Text:
        return self._desc or f"[{self._name}]"

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
    def name(self, name):
        self._name = name

    @property
    def desc(self) -> Text:
        return self._desc or f"[{self._name}]"

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
    _states = set()
    _transitions = dd(list)
    _initial_state = None

    def __init__(self,
                 name: Text,
                 desc: Text = None,
                 model: object = None,
                 *args, **kwargs):

        # There is only one state...
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
        # There is only one state at a time
        return self._state

    @classmethod
    @property
    def states(cls) -> Set[State]:
        return cls._states

    @classmethod
    @property
    def transitions(cls) -> dd[State, Set]:
        return cls._transitions

    @classmethod
    def callbacks_init(cls):
        # Build indexes for state and transition callbacks
        #
        # Note that we store the method function refs, not the bound methods.
        # This distinction is important, because multiple instances of the same
        # StateMachine subclass will share the same callback methods, and this
        # ensures that we always provide the correct instance passed as 'self'.
        cls._initial_state = None
        members = cls.__dict__.keys()
        final_states = 0

        # just in case we're re-initializing, we don't want these class props
        # to pile up with dupes
        cls._states.clear()
        cls._transitions.clear()

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
                cls._states.add(attrib)

            elif isinstance(attrib, Transition):
                if not attrib.name:
                    attrib.name = name
                if ((cond_name := getattr(attrib, 'cond')) is None or
                        getattr(cls, cond_name, None) is None):
                    raise TransitionException(
                        f"Transition {attrib.name} has no 'cond' param, or "
                        f"condition method "
                        f"'{cls.__name__}.{cond_name}' needs implementing")
                if attrib in cls._transitions[attrib.state1]:
                    raise TransitionException(
                        f"Duplicate transition {attrib.name} from "
                        f"{attrib.state1} to {attrib.state2}")
                cls._transitions[attrib.state1].append(attrib)

                # Collect callbacks as partials, in proper firing order.
                # At runtime the 'self' param is added for correct context
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
        if not cls._transitions:
            raise TransitionException("No transitions defined")

    def cycle(self):
        klass = self.__class__

        if self._first_run:
            try:
                if mutex.acquire(blocking=True):
                    self._first_run = False
                    if not getattr(self, '_state', None):
                        raise StateMachineException(
                            "State machine has no current state. Ensure that "
                            "you called super().__init__(*args, **kwargs) "
                            "from your subclass __init__ method.")

                    if not klass.transitions:
                        raise TransitionException(
                            "No transitions were found, or your StateMachine "
                            "subclass is not calling super().__init__(*args, "
                            "**kwargs) from its own __init__ method.")
            finally:
                mutex.release()

        if self._state.final:
            return False

        # Get the transitions for the current state - there must be some,
        # unless the current state is marked final
        if not (candidates := klass.transitions.get(self._state, None)):
            raise TransitionException(
                f"No transitions found from state: {self._state}")

        # Iterate the transitions from current state to other states
        # and check if their condition function matches current context
        did_transition = False
        for trans in candidates:
            if condition_fn := getattr(klass, trans.cond, None):
                if condition_fn(self, trans):
                    # Entered a transition with matching condition..
                    # Let's execute defined callbacks, with 'self' as context
                    for callback in trans.callbacks:
                        callback(self=self)

                    # Move to the next state
                    self._state = trans.state2
                    did_transition = True

                    # Transition complete - we do not look for other matching
                    # transitions
                    break
            else:
                raise TransitionException(
                    f"Condition function {trans.cond} for transition "
                    f"{str(trans)} is not yet implemented")

        if not did_transition:
            logger.warning(
                "No transition or condition was found for state: "
                "%s.  This is possibly due to the condition "
                "function not correctly matching the current context.",
                str(self._state))

    def __getitem__(self, item: Text, something=None) -> Any:
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
