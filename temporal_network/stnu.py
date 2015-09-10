__author__ = 'yupeng'

from collections import namedtuple, defaultdict

StnuEdge = namedtuple('StnuEdge', ['fro', 'to', 'lower_bound', 'upper_bound', 'id'])

class Stnu(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.num_nodes = 0
        self.controllable_edges = []
        self.uncontrollable_edges = []

    def verify_contraints(self):
        pairs = []
        for edge in self.controllable_edges:
            # check bounds on edges
            assert edge.lower_bound <= edge.upper_bound
            pairs.append((edge.fro, edge.to))

        # Controllable edges are not repeated (not two edges connect
        # the same nodes). This could in principle be allowed and then we
        # could normalize by replacing all the edges between a given pair
        # of nodes by a single edge with bound interval equal to an
        # intersection of bound intervals for all the edges connecting
        # that pair of nodes.
        assert len(pairs) == len(set(pairs))

        pairs = []
        input_degree = defaultdict(lambda: 0)
        uncontrollable_starts = set()
        uncontrollable_ends = set()
        for edge in self.uncontrollable_edges:
            # Check bounds on edges. Notice that below 0 is disallowed in
            # contrast to controllable edges
            uncontrollable_starts.add(edge.fro)
            uncontrollable_ends.add(edge.to)
            input_degree[edge.to] += 1
            assert 0 <= edge.lower_bound and edge.lower_bound <= edge.upper_bound
            pairs.append((edge.fro, edge.to))

        # no two uncontrollable edges are one after another in the network.
        assert len(uncontrollable_starts.intersection(uncontrollable_ends)) == 0
        # Controllable edges are not repeated (not two edges connect
        # the same nodes). Here we really mean it. If two edges between
        # a pair of nodes had different bounds network is immediately
        # not DC.
        assert len(pairs) == len(set(pairs))

        # Two uncontrollable edges cannot end in the same node.
        for node in input_degree:
            assert input_degree[node] <= 1

    @property
    def num_edges(self):
        return len(self.uncontrollable_edges) + len(self.controllable_edges)

    @staticmethod
    def from_tpn(tpn):
        stnu = Stnu()

        # In TPN format every node (or event in TPN terminology) has a non-unique name
        # and an unique id. Both of those are strings. For efficiency DC checking algorithms
        # denote each node by a number, such that we can cheaply check their equality.
        event_ids = set()
        stnu.node_id_to_name = {}
        stnu.node_number_to_id = {}
        stnu.node_id_to_number = {}

        for event in tpn.get_events().get_event():
            eid, ename = event.get_id(), event.get_name()
            event_ids.add(eid)
            stnu.node_id_to_name[eid] = ename

        for eid in event_ids:
            next_number = len(stnu.node_number_to_id) + 1
            stnu.node_number_to_id[next_number] = eid
            stnu.node_id_to_number[eid] = next_number

        stnu.num_nodes = len(stnu.node_number_to_id)

        # if line below confuses you, that's expected... We need better automated code generation for parsing...
        for temporal_constraint in tpn.get_temporal_constraints().get_temporal_constraint() + tpn.get_episodes().get_episode():
            # duration can be one of three types - controllable, uncertain and probabilistic
            # here we are only handling the first two cases, which are sorted into two lists
            # in our resulting stnu class.

            controllable_duration = temporal_constraint.get_duration().get_bounded_duration()
            uncertain_duration = temporal_constraint.get_duration().get_set_bounded_uncertain_duration()

            duration = controllable_duration or uncertain_duration
            lower_bound = duration.get_lower_bound()
            upper_bound = duration.get_upper_bound()
            from_event = temporal_constraint.get_from_event()
            to_event = temporal_constraint.get_to_event()
            edge_id = temporal_constraint.get_id()


            edge = StnuEdge(stnu.node_id_to_number[from_event],
                            stnu.node_id_to_number[to_event],
                            lower_bound,
                            upper_bound,
                            edge_id)

            if controllable_duration is not None:
                stnu.controllable_edges.append(edge)
            elif uncertain_duration is not None:
                stnu.uncontrollable_edges.append(edge)

        stnu.verify_contraints()

        return stnu

    def pretty_print(self):
        print('Number of nodes: %d' % self.num_nodes)
        print('Number of edges: %d' % self.num_edges)
        print('Number of controllable edges: %d' % len(self.controllable_edges))
        print('Number of uncontrollable edges: %d' % len(self.uncontrollable_edges))
        print('List of controllable edges:')
        for edge in self.controllable_edges:
            fro, to, lb, ub, id = edge
            if hasattr(self, 'node_number_to_id') and hasattr(self, 'node_id_to_name'):
                fro = self.node_number_to_id[fro]
                to = self.node_number_to_id[to]
            print('    %s -> %s [%f, %f]' % (fro, to, lb, ub))

        print('List of uncontrollable edges:')
        for edge in self.uncontrollable_edges:
            fro, to, lb, ub, id = edge
            if hasattr(self, 'node_number_to_id') and hasattr(self, 'node_id_to_name'):
                fro = self.node_number_to_id[fro]
                to = self.node_number_to_id[to]
            print('    %s -> %s [%f, %f]' % (fro, to, lb, ub))
