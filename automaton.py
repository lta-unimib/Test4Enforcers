from collections import deque

import networkx as nx


class Automaton(object):
    def __init__(self,  states, initial_state, input_act, output_act, transitions, input_label='input', output_label='output'):
        self.states = states
        self.initial_state = initial_state
        self.input_act = input_act
        self.output_act = output_act
        self.actions = input_act | output_act
        self.transitions = transitions

        self.input_label = input_label
        self.output_label = output_label

        self.G = nx.MultiDiGraph()
        self.G.add_edges_from(transitions)

    def transition_cover(self) -> dict:
        """Generate a transition cover set for the automaton.

        Uses BFS and backtracking on edges to discover all possible paths.
        Each key in the returned dictionary represent a node and its value is all
        the possible paths starting from root and terminating in that node.

        Returns:
            dict: Dictionary with nodes as keys and array of paths as values.
        """
        visited = set()
        paths = dict((node, []) for node in self.G.nodes())
        q = deque([])

        # Starting transition. Not existing in the automaton, but useful
        # to represent the starting epsilon which is always part of the
        # transition cover set.
        q.append(((None, self.initial_state, None), []))

        # Until q still has transitions to process
        while q:
            # Pop the oldest appended element
            transition, path = q.popleft()

            # Discard previously visited transitions
            if transition in visited:
                continue
            # Mark as visited
            visited.add(transition)

            _, target, _ = transition
            # Append the current path to the output dictionary
            # in the current node key.
            paths[target].append(path)

            # Enqueue out transitions from the current node.
            for out_transition in self.G.out_edges(target, data=self.input_label):
                # The enqueued element will contain the new path so far for that transition.
                q.append((out_transition, path + [out_transition]))

        return paths

    def check_input_sequences(self, s, sequence):
        """Check if the given input sequence is valid for the node s

        Args:
            s (string): Starting state
            sequence (list): List of transitions to traverse

        Returns:
            bool: Whether the sequence is an input sequence for the state s or not
        """
        if len(sequence) > 0 and sequence[0][0] != s:
            return False

        for node in sequence:
            if node not in self.input_actions(node[0]):
                return False

        return True

    def output_sequences(self, s, sequence):
        """Traverse the graph and track the generated output sequence

        Args:
            s (string): Starting node of the sequence
            sequence (list): The list of transitions to traverse

        Returns:
            list: Output sequence for the given input sequence
        """
        output_sequence = []

        if len(sequence) > 0 and sequence[0][0] != s:
            return sequence

        for node in sequence:
            if node not in self.input_actions(node[0]):
                return False

            u, v, action = node
            for edge in self.G.get_edge_data(u, v).values():
                if edge[self.input_label] == action:
                    output_sequence.append(edge[self.output_label])

        return output_sequence

    def separating_sequence(self, s1, s2):
        for _, _, act1 in self.G.out_edges(s1, data=True):
            for _, _, act2 in self.G.out_edges(s2, data=True):
                if act1[self.input_label] == act2[self.input_label] and act1[self.output_label] != act2[self.output_label]:
                    return act1[self.input_label]

    def separating_family(self, s):
        family = set()

        for state in self.G.nodes:
            if s != state:
                family.add(self.separating_sequence(s, state))

        return family

    def separating_families(self):
        return dict((s, self.separating_family(s)) for s in self.G.nodes)

    def hsi_suite(self):
        suite = set()

        transition_cover = self.transition_cover()
        separating_families = self.separating_families()

        # If graph has only one state, cover all the transitions directly, as no separating family exists
        if self.G.number_of_nodes() == 1:
            for node, paths in transition_cover.items():
                for path in paths:
                    if len(path) > 0:
                        suite.add(tuple(map(lambda x: x[2], path)))
        else:
            # Map<Node, List<Transition<Si, Sj, Action>>>
            for node, paths in transition_cover.items():
                # Set<Input actions that separates node from others>
                for action in separating_families[node]:
                    for path in paths:
                        # Extract actions from every transition of the path
                        actions = tuple(map(lambda x: x[2], path))
                        # Concatenate the input sequence with the separating action
                        suite.add(actions + tuple([action]))

        return suite

    def enforcer_intervention(self, sequence):
        node = self.initial_state

        for action in sequence:
            edges = list(filter(lambda e: e[2]['intercept'] == action, self.G.out_edges(node, data=True)))
            if len(edges) > 0:
                edge = edges[0]
                node = edge[1]
                yield edge[2]['intercept'] != edge[2]['perform']
            else:
                raise Exception(f'Invalid action \'{action}\' in state \'{node}\'')

    def input_actions(self, sx):
        return set(self.G.edges(sx, data=self.input_label))

    def output_actions(self, sx):
        return set(self.G.edges(sx, data=self.output_label))
