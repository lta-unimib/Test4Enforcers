import argparse
import json
import os
import re
from typing import Dict
import xml.etree.ElementTree as ET


parser = argparse.ArgumentParser(description='Convert an editautomaton to a JSON representation', formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=200))
parser.add_argument('input', action='store', help='The automaton source file')
parser.add_argument('-o', '--output', metavar=None, action='store', help='The output folder')


def automaton_to_json(root: ET.ElementTree) -> Dict:
    """Convert an XML tree containing an edit automaton into JSON

    The output automaton will be a Dictionary with the following structure:
    ```
    {
        "states": {...},
        "initial_state": "<node>",
        "actions": {
            "intercepted": {
                ...
            },
            "performed": {
                ...
            }
        },
        "transitions": [
            {
                "source": "<node>",
                "target": "<node>",
                "intercept": "<action>",
                "perform": "<action>"
            }
        ]
    }
    ```

    Args:
        root (ElementTree): The root XML node
    """
    xsi_ns = 'http://www.w3.org/2001/XMLSchema-instance'
    initial_state = None
    states = []
    for state in root.findall('./states'):
        if 'Initial' in state.attrib[f'{{{xsi_ns}}}type']:
            initial_state = state.attrib['name']
        states.append(state.attrib['name'])
    assert(initial_state is not None)

    xml_transitions = root.findall('./transitions')

    variables = extract_variable_assignments(xml_transitions)

    get_state = lambda value: states[int(value.split('.')[1])]
    transform_transition = lambda transition: {
        'source': get_state(transition.attrib['source']),
        'target': get_state(transition.attrib['target']),
        'intercept': map_signature(transition.attrib['interceptedAction'], variables),
        'perform': map_signature(transition.attrib['actionToPerform'], variables),
    }

    return {
        'states': list(set(states)),
        'initial_state': initial_state,
        'actions': {
            'intercepted': list(set(map(lambda action: map_signature(action.attrib['interceptedAction'], variables), xml_transitions))),
            'performed': list(set(map(lambda action: map_signature(action.attrib['actionToPerform'], variables), xml_transitions))),
        },
        'transitions': [transform_transition(transition) for transition in xml_transitions],
    }


def extract_variable_assignments(transitions):
    variables = {}

    for transition in transitions:
        for method in transition.attrib['interceptedAction'].split(';'):
            _, _, params = extract_params(method)
            for param in params:
                if '=' not in param:
                    continue

                name, value = param.split('=')
                if name in variables:
                    raise Exception(f'Multiple values assigned to the same variable name "{name}".')

                variables[name] = value

    return variables


def extract_params(method):
    start = method.rfind('(') + 1
    end = method.rfind(')')
    return start, end, filter(lambda p: len(p) > 0, method[start:end].split(','))


def map_signature(action, variables):
    return ';'.join(map(lambda x: map_method(x, variables), action.split(';')))


def map_method(method, variables):
    method = method.replace('after#', '').replace('before#', '').replace('()', '', method.count('()') - 1)

    start, end, params = extract_params(method)

    params = list(map(lambda p: p.split('=')[1] if '=' in p else p, params))

    if 'new ' in method:
        method = f'{method[:start-1]}.<init>{method[start-1:]}'
        method = method.replace('new ', '')
        start += len('.<init>') - len('new ')
        end += len('.<init>') - len('new ')

    return method[:start] + ''.join(map(lambda p: internal_signature(p, variables), params)) + method[end:]


def internal_signature(param, variables):
    if param in variables:
        print(f'Replacing {param} variable with {variables[param]} value.')
        param = variables[param]

    if param == 'int':
        return 'I'
    if param == 'long':
        return 'J'
    if param == 'boolean':
        return 'Z'
    if param == 'byte':
        return 'B'
    if param == 'short':
        return 'S'
    if param == 'char':
        return 'C'
    if param == 'float':
        return 'F'
    if param == 'double':
        return 'D'
    if param == 'void':
        return 'V'

    internalName = param.replace('.', '/')
    if '[]' in param:
        return f'[L{internalName};'

    return f'L{internalName};'


def convert(automaton_in, automaton_out):
    print('> Checking file existence...')
    if not os.path.exists(automaton_in):
        raise Exception('Input file does not exist or is not readable!')
    print('! File exists', end='\n\n')

    print('> Parsing automaton...')
    xml = ET.parse(automaton_in)
    root = xml.getroot()
    print('! Automaton is a valid XML file', end='\n\n')

    print('> Starting conversion...')
    automaton = automaton_to_json(root)
    print('# Conversion details')
    print(' - States:', len(automaton['states']))
    print(' - Initial state:', automaton['initial_state'])
    print(' - Actions:', len(automaton['actions']['intercepted']) + len(automaton['actions']['performed']))
    print(' - Transitions:', len(automaton['transitions']))
    print('! Conversion complete!', end='\n\n')

    # Save output
    output = automaton_out or automaton_in.replace('.editautomaton', '.json')
    print('> Saving output...')
    with open(output, 'w') as f:
        f.write(json.dumps(automaton, indent=4))
    print(f'! Output saved at: {output}')


if __name__ == '__main__':
    args = parser.parse_args()
    convert(args.input, args.output)
