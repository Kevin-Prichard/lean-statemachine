#!/usr/bin/env python3

import argparse
import ast
import sys
from collections import defaultdict as dd
from enum import Enum
from importlib import import_module
import os
from typing import Text, List, Type, Set, Tuple

import plantuml

from lean import StateMachine, State


DEFAULT_PLANTUML_SERVER = 'http://www.plantuml.com/plantuml/img/'


class GraphFormat(Enum):
    PLANTUML = 'plantuml'
    ASCII = 'ascii'
    SVG = 'svg'
    PNG = 'png'
    JPEG = 'jpeg'
    DEFAULT = SVG


args = None


def get_args(argv: List[str]) -> Tuple[argparse.Namespace,
                                       argparse.ArgumentParser]:
    global args
    parser = argparse.ArgumentParser(
        prog='./graph.py',
        description='Generatee a graph of a Lean StateMachine in a variety '
                    'of formats')
    parser.add_argument(
        '-s', '--source', dest='source_path', type=str,
        action='store', default='examples/gumball_machine.py',
        help='Path to the source file containing the StateMachine subclass.')
    parser.add_argument(
        '--class', '-c', dest='machine_class', type=str,
        action='store', default='GumballStateMachine',
        help='The class name of the StateMachine class to graph, '
             'e.g. "GumballStateMachine"',)
    parser.add_argument(
        '--module', '-m', dest='module_name', type=str,
        action='store', default='examples.gumball_machine',
        help='The fully-qualified modyke name where your StateMachine '
             'subclass is defined, e.g. "examples.gumball_machine".',)
    parser.add_argument(
        '--format', '-f', dest='format', type=str, action='store',
        default=GraphFormat.DEFAULT,)
    parser.add_argument(
        '--server', '-u', dest='server_url', type=str, action='store',
        default=DEFAULT_PLANTUML_SERVER,
        help=f'server to generate from, defaults to {DEFAULT_PLANTUML_SERVER}')
    parser.add_argument(
        '--out', '-o', dest='out', type=str, action='store',
        default=f"{os.path.abspath(os.path.curdir)}/out.png",
        help='Output filename for generated PlantUML image')

    args = parser.parse_args(argv)
    return args, parser


def get_machine_ast(source_path, machine_name) -> ast.ClassDef:
    with open(source_path, "r") as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = getattr(node, 'bases', [])
            for base in bases:
                if base.id == 'StateMachine' and node.name == machine_name:
                    return node


def get_method_body(klass: ast.ClassDef, method_name: Text) -> Text:
    for node in klass.body:
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return ast.unparse(node.body[0].value)


def walk_transition_graph(state: State,
                          transitions: dd[State, Set],
                          buf: List[Text],
                          pairs_visited: set,
                          mach_ast: ast.ClassDef) -> None:

    for trans in transitions.get(state, set()):
        if (state, trans.state2) in pairs_visited:
            continue
        tbody = get_method_body(mach_ast, trans.cond)
        buf.append(f"state {state.name} as \"{state.name}\"")
        buf.append(f"state {trans.state2.name} as \"{trans.state2.name}\"")
        buf.append(f"{state.name} --> {trans.state2.name} : "
                   f"{trans.name}:\\n  {tbody}")
        pairs_visited.add((state, trans.state2))
        if not trans.state2.final:
            walk_transition_graph(trans.state2,
                                  transitions,
                                  buf,
                                  pairs_visited,
                                  mach_ast)


def machine2plantuml(source_path: Text,
                     machine_class: Text,
                     module_name) -> Text:

    machine_module = import_module(module_name)
    machine: Type[StateMachine] = getattr(machine_module, machine_class)

    # Get the state machine's AST, so we can extract logic from event handlers
    mach_ast = get_machine_ast(source_path, machine_class)

    # static initialize the state machine
    machine.callbacks_init()

    # extract its states and transitions
    states = machine.states
    transitions = machine.transitions
    state_initial, state_final = None, None
    for state in states:
        if state.initial:
            state_initial = state
        if state.final:
            state_final = state

    # build the PlantUML markup
    buf = ["@startuml",
           f"title State Diagram for {machine_class}",
           f"state {state_initial.name}",
           f"[*] --> {state_initial.name}"]
    pairs_visited = set()
    for state in transitions.keys():
        walk_transition_graph(state, transitions, buf, pairs_visited, mach_ast)
    if state_final:
        buf.append(f"state {state_final.name}")
        buf.append(f"{state_final.name} --> {state_initial.name}")
        buf.append(f"{state_final.name} --> [*]")
    buf.append("@enduml")

    # done
    return "\n".join(buf)


def plantuml2image(plantuml_markup: Text,
                   server_url: Text,
                   output_pathname: Text) -> None:
    pl = plantuml.PlantUML(url=server_url)
    image_data = pl.processes(plantuml_markup)
    with open(output_pathname, "wb") as out_file:
        out_file.write(image_data)
        print("Written to", output_pathname)


if __name__ == "__main__":
    args, parser = get_args(sys.argv[1:])
    plant_markup = machine2plantuml(
        source_path=args.source_path,
        machine_class=args.machine_class,
        module_name=args.module_name)
    plantuml2image(
        plantuml_markup=plant_markup,
        server_url=args.server_url,
        output_pathname=args.out)
