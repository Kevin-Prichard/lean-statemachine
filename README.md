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
For example, see examples/gumball_machine.py

In the GumballStateMachine example, we pass in an instance of GumballMachineHardware, providing a context / reference to an API external to the state machine subclass.  This allows callbacks to query physical state in order to prompt state change in the state machine, as well as activate API and/or hardware features in response to the state machine's events and changing state.

This keeps intact the boundary between state machines' internal state tracking, and the actual implementation of the processes and/or physical machines that they represent.
