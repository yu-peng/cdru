__author__ = 'yupeng'

from temporal_network.tpnu import Tpnu
from tpn.tpn_autogen import tpn as ParseTpnClass

from collections import defaultdict

from graph_theory import spfa
from controllability.distance_graph_edge import EdgeType, DistanceGraphEdge
from controllability.temporal_consistency import EdgeSupport
import math

class StrongControllability(object):

    @staticmethod
    def check(network):
        if type(network) == ParseTpnClass:
            network = Tpnu.from_tpn_autogen(network)
        elif type(network) == Tpnu:
            pass
        else:
            raise Exception("Wrong type of network passed to strong controllability checking")

        network.initialize()
        alg = Vidal99Reduction()

        return alg.check(network)

class Vidal99Reduction(object):

    """Triangular reduction implementation based on paper "Handling
contingency in temporal constraint networks: from
consistencies to controllabilities" by Thierry VIDAL and Helene FARGIER"""

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
            # assert lb <= ub

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

        def add_uncontrollable(fro, to, lb, ub, edge_id):

            # no negative lower bound
            # no infinite upperbound
            assert lb <= ub
            assert not lb < 0
            assert not math.isinf(ub)

            ub_edge = DistanceGraphEdge(fro, to, ub, EdgeType.SIMPLE, renaming=renaming)
            lb_edge = DistanceGraphEdge(to, fro, -lb, EdgeType.SIMPLE, renaming=renaming)

            if edge_id is not None:
                # Note that the sign for the upper and lower bound supports are reversed
                # Since they are being subtracted during the reduction
                self.edge_support[ub_edge] = EdgeSupport.base({(EdgeSupport.UPPER, edge_id): -1,})
                self.edge_support[lb_edge] = EdgeSupport.base({(EdgeSupport.LOWER, edge_id): 1,})
            else:
                self.edge_support[ub_edge] = EdgeSupport.base({})
                self.edge_support[lb_edge] = EdgeSupport.base({})

            #edge_list.append(ub_edge)
            #edge_list.append(lb_edge)
            #contingent_nodes.append(to)
            if to in contingent_edges_at_node:
                collection = contingent_edges_at_node[to]
                collection.append(lb_edge)
                collection.append(ub_edge)
            else:
                collection = []
                collection.append(lb_edge)
                collection.append(ub_edge)
                contingent_edges_at_node[to] = collection

        encoded_node_pairs = {}
        # Encode initial edges
        for e in network.temporal_constraints.values():
            # We only consider constraints that are active
            if e.activated:
                if e.fro == 0 or e.to == 0:
                    raise Exception("Node with id zero is not allowed (see documentation for check function.)")
                if e.controllable:
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
                else:
                    # Make sure no two edges share the same from and to nodes
                    if (e.fro,e.to) not in encoded_node_pairs:
                        add_uncontrollable(e.fro,e.to,e.get_lower_bound(),e.get_upper_bound(),e.id)
                        encoded_node_pairs[(e.fro,e.to)] = True
                    else:
                        new_node = num_nodes + 1
                        num_nodes += 1
                        renaming[new_node] = renaming[e.to] + "'"
                        add_uncontrollable(e.fro,new_node,e.get_lower_bound(),e.get_upper_bound(),e.id)
                        add_controllable(new_node,e.to,0,0,None)

        # Execute triangular reduction procedure on the edges
        reduced_edges = []
        for edge in edge_list:

            new_edges = []

            if edge.fro in contingent_edges_at_node:
                contingent_edges = contingent_edges_at_node[edge.fro]
                for contingent_edge in contingent_edges:
                    if contingent_edge.fro == edge.fro:
                        reduced_edge = DistanceGraphEdge(contingent_edge.to, edge.to, edge.value-contingent_edge.value, EdgeType.SIMPLE, renaming=renaming)
                        self.edge_support[reduced_edge] = EdgeSupport.derived(edge, contingent_edge)
                        new_edges.append(reduced_edge)
                        # print("Reducing: " + str(edge) + " and " + str(contingent_edge))
                        # print("Adding reduced from edge: " + str(reduced_edge.fro) + "->" + str(reduced_edge.to) + " (" + str(reduced_edge.value) + ")")
            else:
                new_edges.append(edge)

            for new_edge in new_edges:
                if new_edge.to in contingent_edges_at_node:
                    contingent_edges = contingent_edges_at_node[edge.to]
                    for contingent_edge in contingent_edges:
                        if contingent_edge.to == edge.to:
                            reduced_edge = DistanceGraphEdge(edge.fro, contingent_edge.fro, edge.value-contingent_edge.value, EdgeType.SIMPLE, renaming=renaming)
                            self.edge_support[reduced_edge] = EdgeSupport.derived(edge, contingent_edge)
                            reduced_edges.append(reduced_edge)
                            # print("Reducing: " + str(new_edge) + " and " + str(contingent_edge))
                            # print("Adding reduced to edge: " + str(reduced_edge.fro) + "->" + str(reduced_edge.to) + " (" + str(reduced_edge.value) + ")")
                else:
                    reduced_edges.append(new_edge)

        return num_nodes, reduced_edges

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


    def extract_conflict(self,edge_list):
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
            # print(str(edge))
            if edge not in expression_cache:
                if self.edge_support[edge].type == EdgeSupport.BASE:
                    # print("Exp: " + str(self.edge_support[edge].expression))
                    expression_cache[edge] = self.edge_support[edge].expression
                else:
                    # print("Parent: " + str(len(self.edge_support[edge].parents)))
                    expression_cache[edge] = combine_expressions(
                        [get_edge_expression(parent) for parent in self.edge_support[edge].parents]
                    )
            return expression_cache[edge]

        # The code below has dual purpose
        #     1) It computes conflict spanning entire cycle
        #     2) It trigers conflict calculations for all the edge on that cycle
        #        and edges on reductions of those edges (as well as reductions of
        #        edges on reductions and so on...)

        # neg_value = 0
        # for edge in edge_list:
        #     neg_value += edge.value

        # print('NValue: ' + str(neg_value) + "   / size: " + str(len(edge_list)))
        big_conflict = combine_expressions([get_edge_expression(edge) for edge in edge_list])
        conflicts.append(big_conflict)

        return conflicts
