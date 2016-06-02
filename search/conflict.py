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
        hasRelaxable = False
        for base_expression, coefficient in expression.items():
            constraint_type, edge_id = base_expression
            constraint = tpnu.temporal_constraints[edge_id]
            if constraint_type == EdgeSupport.LOWER:
                negative_cycle.add_constraint(constraint, 0, coefficient)
                if constraint.relaxable_lb:
                    hasRelaxable = True
            else:
                negative_cycle.add_constraint(constraint, 1, coefficient)
                if constraint.relaxable_ub:
                    hasRelaxable = True

            self.add_guard_assignments(constraint.guards)

        if hasRelaxable:
            self.negative_cycles.add(negative_cycle)

    def add_negative_cycles(self,cycles,tpnu):
        # print("Adding " + str(len(cycles)) + " cycles")
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
            curr_value = 0

            for constraint, bound in negative_cycle.constraints.keys():

                coefficient = negative_cycle.constraints[(constraint, bound)]

                if coefficient >= 0:
                    expression_str.append(PLUS)
                else:
                    expression_str.append(MINUS)

                if bound == 0:
                    expression_str.append('%d%s(%s:%s->%s)[%.4f,%.4f]' % (abs(coefficient), 'LB', constraint.name, constraint.fro, constraint.to, constraint.lower_bound, constraint.upper_bound))
                    curr_value += coefficient*constraint.get_lower_bound()
                elif bound == 1:
                    expression_str.append('%d%s(%s:%s->%s)[%.4f,%.4f]' % (abs(coefficient), 'UB', constraint.name, constraint.fro, constraint.to, constraint.lower_bound, constraint.upper_bound))
                    curr_value += coefficient*constraint.get_upper_bound()

            expression_str.append(' = ' + str(curr_value))

            print(''.join(expression_str))

            if (curr_value >= 0):
                raise Exception("Positive conflict value detected: " + str(curr_value))

class NegativeCycle(object):

    def __init__(self):
        # a negative cycle is a map
        # between the lower and upper bounds
        # of a constraint to a coefficient

        self.constraints = {}

    def add_constraint(self,constraint, bound, coefficient):
        self.constraints[(constraint,bound)] = coefficient

    def pretty_print(self):
        PLUS = ' + '
        MINUS = ' - '
        expression_str = []
        curr_value = 0

        for constraint, bound in self.constraints.keys():

            coefficient = self.constraints[(constraint, bound)]

            if coefficient >= 0:
                expression_str.append(PLUS)
            else:
                expression_str.append(MINUS)

            if bound == 0:
                expression_str.append('%d%s(%s:%s->%s)[%.4f,%.4f]' % (
                abs(coefficient), 'LB', constraint.name, constraint.fro, constraint.to, constraint.lower_bound,
                constraint.upper_bound))
                curr_value += coefficient * constraint.get_lower_bound()
            elif bound == 1:
                expression_str.append('%d%s(%s:%s->%s)[%.4f,%.4f]' % (
                abs(coefficient), 'UB', constraint.name, constraint.fro, constraint.to, constraint.lower_bound,
                constraint.upper_bound))
                curr_value += coefficient * constraint.get_upper_bound()

        expression_str.append(' = ' + str(curr_value))

        print(''.join(expression_str))

