__author__ = 'yupeng'

from temporal_network.tpnu import Tpnu
from tpn.tpn_autogen import tpn as ParseTpnClass

from collections import defaultdict

from graph_theory import spfa
from controllability.distance_graph_edge import EdgeType, DistanceGraphEdge
import math

class TemporalConsistency(object):

    @staticmethod
    def check(network):
        if type(network) == ParseTpnClass:
            network = Tpnu.from_tpn_autogen(network)
        elif type(network) == Tpnu:
            pass
        else:
            raise Exception("Wrong type of network passed to temporal consistency checking")

        network.initialize()
        alg = NrgativeCycleDetection()

        return alg.check(network)


class NrgativeCycleDetection(object):

    """Negative Cycle Detection Implementation"""

    def __init__(self):
        self.edge_support = {}

    def check(self, network):

        # Generate distance graph from stnu.
        num_nodes, all_edges = self.generate_graph_from_tpnu(network)

        potential_conflict = None
        negative_cycle = self.consistent(num_nodes, all_edges)

        if negative_cycle is not None:

            # extract a conflict from the negative cycle detected
            # give all edges in the negative cycle
            # we take the sum of their support
            # and map back to the lower and upper bounds
            # of constraints in the tpnu

            # the output is a dictionary
            # that maps the constraints' lower and upper bounds
            # to the coefficient in the array

            # We need to trace the support for the edges
            # in order to extract a linear express over them

            conflict = self.extract_conflict(negative_cycle)
            # self.expressions_pretty_print(conflict)
            potential_conflict = conflict

        return potential_conflict

    def generate_graph_from_tpnu(self, network):
        """Generates distance graph from a tpnu"""

        num_nodes = network.num_nodes
        contingent_edges_at_node = {}
        edge_list = []

        if hasattr(network, 'node_number_to_id'):
            renaming = network.node_number_to_id

        def add_controllable(fro, to, lb, ub, edge_id):

            # lb cannot be larger than ub
            assert lb <= ub

            ub_edge = DistanceGraphEdge(fro, to, ub, EdgeType.SIMPLE, renaming=renaming)
            lb_edge = DistanceGraphEdge(to, fro, -lb, EdgeType.SIMPLE, renaming=renaming)

            if edge_id is not None:
                self.edge_support[ub_edge] = EdgeSupport.base({(EdgeSupport.UPPER, edge_id): 1,})
                self.edge_support[lb_edge] = EdgeSupport.base({(EdgeSupport.LOWER, edge_id): -1,})
            else:
                self.edge_support[ub_edge] = EdgeSupport.base({})
                self.edge_support[lb_edge] = EdgeSupport.base({})

            if not math.isinf(ub):
                edge_list.append(ub_edge)
            # else:
            #     print("Ignoring +inf UB of " + e.id)

            if not math.isinf(lb):
                edge_list.append(lb_edge)
            # else:
            #     print("Ignoring -inf LB of " + e.id)

        encoded_node_pairs = {}
        # Encode initial edges
        for e in network.temporal_constraints.values():
            # We only consider constraints that are active
            if e.activated:
                if e.fro == 0 or e.to == 0:
                    raise Exception("Node with id zero is not allowed (see documentation for check function.)")

                # Make sure no two edges share the same from and to nodes
                if (e.fro,e.to) not in encoded_node_pairs:
                    add_controllable(e.fro,e.to,e.get_lower_bound(),e.get_upper_bound(),e.id)
                    encoded_node_pairs[(e.fro,e.to)] = True
                else:
                    new_node = num_nodes + 1
                    num_nodes += 1
                    renaming[new_node] = renaming[e.to] + "'"
                    add_controllable(e.fro,new_node,e.get_lower_bound(),e.get_upper_bound(),e.id)
                    add_controllable(new_node,e.to,0,0,None)

        return num_nodes, edge_list

    def consistent(self,num_nodes, edge_list):
        """Calculates consistency of reduced STNU.
        Returns one parameter:
            success - true if consistent
        """
        weights = {}
        neighbor_list = defaultdict(lambda: set())

        spfa_graph_to_distance_graph = {}

        for e in edge_list:
            pair = (e.fro, e.to)
            if (pair not in weights) or (weights[pair] > e.value):
                spfa_graph_to_distance_graph[pair] = e
                neighbor_list[e.fro].add(e.to)
                weights[pair] = e.value

        # Like in Johnson's algorithm we add node 0 artificially
        for node in range(1, num_nodes + 1):
            weights[(0,node)] = 0
            neighbor_list[0].add(node)

        distances, negative_cycle = spfa(source = 0,
                                     num_nodes=num_nodes + 1,
                                     weights=weights,
                                     neighbor_list=neighbor_list)

        edges_on_cycle = None

        if negative_cycle is not None:
            assert(0 not in negative_cycle)
            edges_on_cycle = []
            nvalue = 0
            # print('---- to edge ')
            for fro, to in zip(negative_cycle, negative_cycle[1:] + negative_cycle[:1]):
                edge = spfa_graph_to_distance_graph[(fro, to)]
                edges_on_cycle.append(edge)
                nvalue += edge.value
                # print(str(fro) + '->' + str(to) + ':' + str(edge.value))
            # print('Cycle size: ' + str(len(edges_on_cycle)) + ' with value ' + str(nvalue))

            if nvalue > 0:
                raise Exception('Positive cycle value detected!');

        return edges_on_cycle


    def extract_conflict(self,edge_list, include_combined=True):
        conflicts = []
        expression_cache = {}

        # TODO(peng): benchmark and thing about maybe avoiding copies
        def combine_expressions(expressions):
            result = defaultdict(lambda: 0)
            for expression in expressions:
                for base_expression, coefficient in expression.items():
                    result[base_expression] += coefficient
            return result

        def get_edge_expression(edge):
            if edge not in expression_cache:

                if self.edge_support[edge].type == EdgeSupport.BASE:
                    expression_cache[edge] = self.edge_support[edge].expression
                else:
                    # Check if the current edge is a moat and provides a tighter bound
                    new_neg_value = neg_value

                    expression_cache[edge] = combine_expressions(
                        [get_edge_expression(parent) for parent in self.edge_support[edge].parents]
                    )
            return expression_cache[edge]

        # The code below has dual purpose
        #     1) It computes conflict spanning entire cycle
        #     2) It trigers conflict calculations for all the edge on that cycle
        #        and edges on reductions of those edges (as well as reductions of
        #        edges on reductions and so on...)

        neg_value = 0
        for edge in edge_list:
            neg_value += edge.value

        if include_combined:
            # print('NValue: ' + str(neg_value))
            big_conflict = combine_expressions([get_edge_expression(edge) for edge in edge_list])
            conflicts.append(big_conflict)
        else:
            # print('Nedge: ' + str(neg_value))
            combine_expressions([get_edge_expression(edge,) for edge in edge_list])

        return conflicts

class EdgeSupport(object):
    BASE = 1
    DERIVED = 2
    UPPER = 1
    LOWER = 2

    @staticmethod
    def base(expression):
        es = EdgeSupport()
        es.type = EdgeSupport.BASE
        es.expression = expression
        return es

    @staticmethod
    def derived(parent1, parent2):
        es = EdgeSupport()
        es.type = EdgeSupport.DERIVED
        es.parents = [parent1, parent2]
        return es
