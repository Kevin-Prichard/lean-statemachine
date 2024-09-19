# lean-statemachine
A simple and lean state machine implementation.  With observer callbacks, transitions and events.

## Introduction
This state machine package is a stripped-down framework for implementing state machines in Python.  It is designed to be simple and easy to use, with a minimum of overhead, a lightweight implementation that can be easily integrated into other projects.

The package provides a `StateMachine` class that you subclass to create a state machine.  The subclass should define the States and Transitions that the machine can make.  You define callbacks on the machine subclass, which are called at various events and phases as the machine progresses through the lifecycle you have defined.  Once instantiated, you'll externally cycle through each state. The machine will call the appropriate callbacks as it transitions from state to state.  You may define a graph of states that has multiple branches and endpoints, with travel along the branches controlled by the transitions and their qualifying condition functions that you define.


## Installation
The package can be installed using pip:
```bash
pip install lean-statemachine
```

## Usage
For example:
```python
from leanmachine import StateMachine, State

class GumballMachine(StateMachine):
    ready = State('ready', 'The machine is at rest and ready to begin a purchase cycle', initial=True)
    coin_dropped = State('coin_dropped', 'A coin has been inserted into the machine')
    crank_turned = State('crank_turned', 'The crank has been turned, and the machine is moving a gumball into the dispenser slot')
    gumball_dispensed = State('gumball_dispensed', 'A gumball has been dispensed to the customer')
    crank_returned = State('crank_returned', 'The crank has been returned to its original position', final=True)

    ready.to(coin_dropped, name='coin_inserted', cond='on_coin_inserted', description='A coin has been inserted into the machine')
    coin_dropped.to(crank_turned, name='crank_turned', cond='on_crank_turned', description='The crank has been turned')
    crank_turned.to(gumball_dispensed, name='gumball_dispensed', cond='on_gumball_dispensed', description='A gumball has been dispensed')
    gumball_dispensed.to(crank_returned, name='crank_returned', cond='on_crank_returned', description='The crank has been returned to its original position')

