from collections import defaultdict
from queue import PriorityQueue

from graph_theory import spfa
from controllability.distance_graph_edge import EdgeType, DistanceGraphEdge
import math

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

class MorrisN4Dc(object):
    """Implementation based on paper "A Structural Characterization of Temporal
    Dynamic Controllability" by Paul Morris"""

    def __init__(self):
        self.edge_support = {}
        self.moat_edges = set()

    def generate_graph_from_tpnu(self, network):
        """Generates graph of edges from a tpnu"""

        num_nodes = network.num_nodes
        edge_list = []

        if hasattr(network, 'node_number_to_id'):
            renaming = network.node_number_to_id

        def add_controllable(fro, to, lb, ub, edge_id):

            # lb cannot be larger than ub
            assert lb <= ub

            ub_edge = DistanceGraphEdge(fro, to, ub, EdgeType.SIMPLE, renaming=renaming)
            lb_edge = DistanceGraphEdge(to, fro, -lb, EdgeType.SIMPLE, renaming=renaming)
            if edge_id is not None:
                self.edge_support[ub_edge] = EdgeSupport.base({
                                                                 (EdgeSupport.UPPER, edge_id): 1,
                                                              })
                self.edge_support[lb_edge] = EdgeSupport.base({
                                                                  (EdgeSupport.LOWER, edge_id): -1,
                                                              })
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

        def add_uncontrollable(fro, new_node, to, lb, ub, edge_id):

            # no negative lower bound
            # no infinite upperbound
            assert lb <= ub
            assert not lb < 0
            assert not math.isinf(ub)

            if new_node is not None:
                lb_ub_edge = DistanceGraphEdge(fro, new_node, lb, EdgeType.SIMPLE, renaming=renaming)
                lb_lb_edge = DistanceGraphEdge(new_node, fro, -lb, EdgeType.SIMPLE, renaming=renaming)
                self.edge_support[lb_ub_edge] = EdgeSupport.base({
                                                                    (EdgeSupport.LOWER, edge_id): 1,
                                                                 })
                self.edge_support[lb_lb_edge] = EdgeSupport.base({
                                                                    (EdgeSupport.LOWER, edge_id): -1,
                                                                })

                edge_list.append(lb_ub_edge)
                edge_list.append(lb_lb_edge)
            else:
                new_node = fro

            ub_edge = DistanceGraphEdge(new_node, to, ub-lb, EdgeType.SIMPLE, renaming=renaming)
            lb_edge = DistanceGraphEdge(to, new_node, 0, EdgeType.SIMPLE, renaming=renaming)

            self.edge_support[ub_edge] = EdgeSupport.base({
                                                              (EdgeSupport.LOWER, edge_id): -1,
                                                              (EdgeSupport.UPPER, edge_id): 1,
                                                          })
            self.edge_support[lb_edge] = EdgeSupport.base({})

            ub_cond_edge = DistanceGraphEdge(to, new_node, lb-ub, EdgeType.UPPER_CASE, to, renaming=renaming)
            lb_cond_edge = DistanceGraphEdge(new_node, to, 0, EdgeType.LOWER_CASE, to, renaming=renaming)

            self.edge_support[ub_cond_edge] =  EdgeSupport.base({
                                                                (EdgeSupport.LOWER, edge_id): 1,
                                                                (EdgeSupport.UPPER, edge_id): -1,
                                                           })
            self.edge_support[lb_cond_edge] = EdgeSupport.base({})

            edge_list.append(ub_edge)
            edge_list.append(lb_edge)
            edge_list.append(ub_cond_edge)
            edge_list.append(lb_cond_edge)


        K = 0
        encoded_node_pairs = {}
        for e in network.temporal_constraints.values():
            # We only consider constraints that are active
            if e.activated:
                if e.fro == 0 or e.to == 0:
                    raise Exception("Node with id zero is not allowed (see documentation for check function.)")
                if e.controllable:
                    # Make sure no two edges share the same from and to nodes
                    if (e.fro,e.to) in encoded_node_pairs:
                        add_controllable(e.fro,e.to,e.get_lower_bound(),e.get_upper_bound(),e.id)
                        encoded_node_pairs[(e.fro,e.to)] = True
                    else:
                        new_node = num_nodes + 1
                        num_nodes += 1
                        renaming[new_node] = renaming[e.to] + "'"
                        add_controllable(e.fro,new_node,e.get_lower_bound(),e.get_upper_bound(),e.id)
                        add_controllable(new_node,e.to,0,0,None)
                else:
                    K += 1
                    if e.lower_bound == 0:
                        add_uncontrollable(e.fro,None,e.to,e.get_lower_bound(),e.get_upper_bound(), e.id)
                        encoded_node_pairs[(e.fro,e.to)] = True
                    else:
                        # contingent edges with bounds [l, u] can be normalized to edge
                        # can be replaced by requirement edge [l,l] followed by upper case edge
                        new_node = num_nodes + 1
                        num_nodes += 1
                        renaming[new_node] = renaming[e.fro] + "'"
                        add_uncontrollable(e.fro, new_node, e.to, e.get_lower_bound(), e.get_upper_bound(), e.id)

        return num_nodes, edge_list, K

    def allmax(self, num_nodes, edge_list):
        """Calculates allmax projection of STNU (see section 2.2).
        Returns two parameters:
            success - true if consistent
            potentials - potentials for use in Dijkstra algorithm
        """
        weights = {}
        neighbor_list = defaultdict(lambda: set())

        spfa_graph_to_distance_graph = {}

        for e in edge_list:
            if e.edge_type != EdgeType.LOWER_CASE:
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

        return (distances, edges_on_cycle)



    def reduce_edge(self, edge1, edge2):

        # X ---edge1----> Y ----edge2----> Z
        assert edge2.fro == edge1.to
        new_fro = edge1.fro
        new_to = edge2.to
        new_value = edge1.value + edge2.value
        new_type = None
        new_maybe_letter = None

        # UPPER CASE REDUCTION
        if edge1.edge_type == EdgeType.SIMPLE and edge2.edge_type == EdgeType.UPPER_CASE:
            new_maybe_letter = edge2.maybe_letter
            new_type = EdgeType.UPPER_CASE

        # LOWER CASE REDUCTION
        elif (edge1.edge_type == EdgeType.LOWER_CASE and edge2.edge_type == EdgeType.SIMPLE and
                edge2.value < 0):
            new_type = EdgeType.SIMPLE

        # CROSS CASE REDUCTION
        elif (edge1.edge_type == EdgeType.LOWER_CASE and edge2.edge_type == EdgeType.UPPER_CASE and
                edge2.value < 0 and edge1.maybe_letter != edge2.maybe_letter):
            new_maybe_letter = edge2.maybe_letter
            new_type = EdgeType.UPPER_CASE

        # NO-CASE REDUCITON
        elif edge1.edge_type == EdgeType.SIMPLE and edge2.edge_type == EdgeType.SIMPLE:
            new_type = EdgeType.SIMPLE

        if new_type is None:
            # not reduction matched
            return None

        if new_type == EdgeType.UPPER_CASE:
            # try applying LABEL REMOVAL
            # If you thing about this for our purposes SIMPLE edge is strictly
            # better than upper case.
            if new_value >= 0:
                new_type = EdgeType.SIMPLE
                new_maybe_letter = None

        new_edge = DistanceGraphEdge(new_fro, new_to, new_value, new_type, new_maybe_letter, renaming=edge1.renaming)
        self.edge_support[new_edge] = EdgeSupport.derived(edge1, edge2)
        # if (new_edge.fro == new_edge.to and new_edge.value < 0):
        #     print('combine \t%s \twith \t%s \tto get \t%s' %(edge1, edge2, new_edge))
        #     return None

        return new_edge


    def reduce_lower_case(self, num_nodes, edge_list, potentials, lc_edge):
        new_edges = set()

        # Notice that here we are going to be using Johnson's algorithm in
        # a nonintuitive way, we will remove some edges from the original
        # graph which we use to calculate potentials. If you look through
        # proof of Johnson's algorithms you will notice that removing edges
        # never invalidate the key properties of potentials
        outgoing_edges = defaultdict(lambda: [])
        for edge in edge_list:
            # Ignore lower case edges and upper-case edges with the same letter as lc_edge
            # (paper terminology: breach)
            if (edge.edge_type == EdgeType.LOWER_CASE or
                    (edge.edge_type == EdgeType.UPPER_CASE and
                    edge.maybe_letter == lc_edge.maybe_letter)):
                continue
            outgoing_edges[edge.fro].append(edge)
        # distance in shortest path's graph
        reduced_edge = [None] * (num_nodes + 1)
        distance = [None] * (num_nodes + 1)
        visited = [False] * (num_nodes + 1)

        source = lc_edge.to
        distance[source] = 0

        q = PriorityQueue()
        q.put((0, source))

        #print 'processing LCE %s' % (lc_edge,)

        while not q.empty():
            _, node = q.get()
            if visited[node]:
                continue
            #print 'visiting %d' % node
            visited[node] = True
            for edge in outgoing_edges[node]:
                neighbor = edge.to
                edge_value_potential = edge.value + potentials[edge.fro] - potentials[edge.to]
                if (distance[neighbor] is None or
                        distance[neighbor] > distance[node] + edge_value_potential):
                    # add calculate reduced edge that lead us here
                    if reduced_edge[node] is None:
                        new_reduced_edge = edge
                    else:
                        new_reduced_edge = self.reduce_edge(reduced_edge[node], edge)
                    if new_reduced_edge is None:
                        # cannot make a reduction
                        continue
                    reduced_edge[neighbor] = new_reduced_edge
                    distance[neighbor] = distance[node] + edge_value_potential
                    q.put((distance[neighbor], neighbor))
                    # This the reduced distance as described in the book, excluding the effect of
                    # potentials
                    real_reduced_distance = distance[neighbor] + potentials[neighbor] - potentials[source]
                    # check if we have a moat
                    if real_reduced_distance < 0:
                        relevant_edge = self.reduce_edge(lc_edge, reduced_edge[neighbor])

                        if relevant_edge is not None:
                            #print '^^ moat ^^'
                            new_edges.add(relevant_edge)

                            # record another conflict
                            # based on this moat edge
                            # in case we detect a conflict later,
                            # this can be one negative cycle
                            # since if this moat does not exist,
                            # we will not add this edge,
                            # the resulting conflict would be different

                            self.moat_edges.add(relevant_edge)

                            # return immediately if an edge with the same from and to
                            # and has negative value is detected. Since it itself is already
                            # a negative cycle.
                            if (relevant_edge.fro == relevant_edge.to and relevant_edge.value < 0):
                                return relevant_edge

        #for edge in list(new_edges):
        #    print '   %s' % (edge,)

        return list(new_edges)

    def extract_conflict(self, edge_list, include_combined=True):
        conflicts = []
        expression_cache = {}

        # TODO(peng): benchmark and thing about maybe avoiding copies
        def combine_expressions(expressions):
            result = defaultdict(lambda: 0)
            for expression in expressions:
                for base_expression, coefficient in expression.items():
                    result[base_expression] += coefficient
            return result

        def get_edge_expression(edge,neg_value):
            if edge not in expression_cache:

                if self.edge_support[edge].type == EdgeSupport.BASE:
                    expression_cache[edge] = self.edge_support[edge].expression
                else:
                    # Check if the current edge is a moat and provides a tighter bound
                    if edge in self.moat_edges and edge.value > neg_value:
                        new_neg_value = edge.value
                    else:
                        new_neg_value = neg_value

                    expression_cache[edge] = combine_expressions(
                        [get_edge_expression(parent,new_neg_value) for parent in self.edge_support[edge].parents]
                    )
                # each edge only gets it's cache to be computed once
                # so we will only add expression for the edge one time
                # assuming the same edge does not appear represented
                # by different objects. This should not happen, but
                # hopefully this comment confused you at least a little.
                if edge in self.moat_edges and edge.value > neg_value:
                    conflicts.append(expression_cache[edge])
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
            big_conflict = combine_expressions([get_edge_expression(edge,neg_value) for edge in edge_list])
            conflicts.append(big_conflict)
        else:
            # print('Nedge: ' + str(neg_value))
            combine_expressions([get_edge_expression(edge,-100000) for edge in edge_list])

        return conflicts

    def expressions_pretty_print(self, expressions):
        for expression in expressions:
            PLUS = ' + '
            MINUS = ' - '
            expression_str = []
            for base_expression, coefficient in expression.items():
                if coefficient >= 0:
                    expression_str.append(PLUS)
                else:
                    expression_str.append(MINUS)
                constraint_type, edge_id = base_expression
                constraint_type_str = {
                    EdgeSupport.LOWER:'LB',
                    EdgeSupport.UPPER:'UB'
                }[constraint_type]
                expression_str.append('%d%s(%s)' % (abs(coefficient), constraint_type_str, edge_id))

            print(''.join(expression_str))


    def check(self, network):
        """Implementation of pseudocode from end of section 3 of one of the Morris 06 paper.

        Implementation assumes that nodes are numbered from 1 to num_nodes.
        All the edges should only use integers from range [1, num_nodes]
        as their to and fro values.

        (it's good though, because speed and shit.
        """
        # Number of uncontrollable edge determines upper bound on number of algorithm iterations.

        # Generate distance graph from stnu.
        num_nodes, new_edges, K = self.generate_graph_from_tpnu(network)

        # body of algorithm.
        potential_conflict = None
        completed_iterations = 0
        all_edges = []

        while len(new_edges) > 0 and completed_iterations <= K:
            # add edges from previous iteration's reductions
            all_edges.extend(new_edges)
            new_edges = []
            # check consistency in allmax projection of distance graph.
            potentials, negative_cycle = self.allmax(num_nodes, all_edges)

            # if allmax projection contains negative cycle that means that STNU is not
            # dynamically controllable.


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

                conflict =  self.extract_conflict(negative_cycle)
                # self.expressions_pretty_print(conflict)
                potential_conflict = conflict
                break

            # try to reduce all the lower case edges.
            for e in all_edges:
                if e.edge_type == EdgeType.LOWER_CASE:
                    reduced_edges = self.reduce_lower_case(num_nodes,
                                                           all_edges,
                                                           potentials,
                                                           e)

                    if type(reduced_edges) is DistanceGraphEdge:
                        potential_conflict = self.extract_conflict([reduced_edges],include_combined=False)
                        return potential_conflict

                    new_edges.extend(reduced_edges)
            completed_iterations += 1

            # Assuming the theory from the paper checks out. We need one extra
            # iteration to verify that no edge was actually added.
            assert completed_iterations <= K + 1

        return potential_conflict