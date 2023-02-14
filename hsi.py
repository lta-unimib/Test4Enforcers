import json
import os

from automaton import Automaton


def load_as_dict(path) -> dict:
    """Load the json automaton as a dict.

    The resulting output will have the following structure:
        {
            "states": set of states,
            "initial_state": the starting state name,
            "input_act": set of intercepted actions,
            "output_act": set of performed actions,
            "transitions": set of transitions,
        }

    Args:
        path (string): filename of the converted automaton

    Returns:
        dict: a dictionary object with an I/O automaton structure
    """
    with open(path) as f:
        data = json.loads(f.read())

    return {
        'states': set(data['states']),
        'initial_state': data['initial_state'],
        'input_act': set(data['actions']['intercepted']),
        'output_act': set(data['actions']['performed']),
        'transitions': map(lambda x: (
            x.pop('source'),
            x.pop('target'),
            { **x }
        ), data['transitions'])
    }


def get_suite(path):
    data = load_as_dict(path)
    automaton = Automaton(**data, input_label='intercept', output_label='perform')

    hsi_suite = automaton.hsi_suite()
    # print(*hsi_suite, sep='\n')
    # print()

    hsi_suite_with_flags = [list(zip(suite, automaton.enforcer_intervention(suite))) for suite in hsi_suite]
    # print(*hsi_suite_with_flags, sep='\n')

    return list(data['input_act']), hsi_suite_with_flags


if __name__ == '__main__':
    actions, suite = get_suite(os.path.join(os.getcwd(), 'resources', 'automaton', 'foocam.json'))
    print(actions)
    print(*suite, sep='\n')
