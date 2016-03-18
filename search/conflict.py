__author__ = 'yupeng'

from controllability.morris_n4_dc import EdgeSupport

class Conflict(object):

    def __init__(self):
        self.assignments = set()
        self.negative_cycles = set()

    def add_assignment(self,assignment):
        self.assignments.add(assignment)
        self.add_guard_assignments(assignment.decision_variable.guards)

    def add_guard_assignments(self,guards):
        for guard in guards:
            self.add_assignment(guard)
            self.add_guard_assignments(guard.decision_variable.guards)

    def add_negative_cycle(self,expression,tpnu):

        # Each cycle is a linear expression defined over the lower and upper bounds
        # of some constraints

        negative_cycle = NegativeCycle()
        for base_expression, coefficient in expression.items():

            constraint_type, edge_id = base_expression
            constraint = tpnu.temporal_constraints[edge_id]
            if constraint_type == EdgeSupport.LOWER:
                negative_cycle.add_constraint(constraint, 0, coefficient)
            else:
                negative_cycle.add_constraint(constraint, 1, coefficient)

            self.add_guard_assignments(constraint.guards)

        self.negative_cycles.add(negative_cycle)

    def add_negative_cycles(self,cycles,tpnu):
        for cycle in cycles:
            self.add_negative_cycle(cycle,tpnu)



    def pretty_print(self):

        print("Conflict ASN#:"+str(len(self.assignments))+" NC#:"+str(len(self.negative_cycles)))

        for assignment in self.assignments:
            assignment.pretty_print()

        for negative_cycle in self.negative_cycles:
            PLUS = ' + '
            MINUS = ' - '
            expression_str = []
            for constraint, bound in negative_cycle.constraints.keys():

                coefficient = negative_cycle.constraints[(constraint, bound)]

                if coefficient >= 0:
                    expression_str.append(PLUS)
                else:
                    expression_str.append(MINUS)

                if bound == 0:
                    expression_str.append('%d%s(%s:%s->%s)[%.4f,%.4f]' % (abs(coefficient), 'LB', constraint.name, constraint.fro, constraint.to, constraint.lower_bound, constraint.upper_bound))
                elif bound == 1:
                    expression_str.append('%d%s(%s:%s->%s)[%.4f,%.4f]' % (abs(coefficient), 'UB', constraint.name, constraint.fro, constraint.to, constraint.lower_bound, constraint.upper_bound))

            print(''.join(expression_str))

class NegativeCycle(object):

    def __init__(self):
        # a negative cycle is a map
        # between the lower and upper bounds
        # of a constraint to a coefficient

        self.constraints = {}

    def add_constraint(self,constraint, bound, coefficient):
        self.constraints[(constraint,bound)] = coefficient
