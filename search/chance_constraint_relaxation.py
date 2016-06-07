__author__ = 'yupeng'


class ChanceConstraintRelaxation(object):

    def __init__(self, constraint):
        self.constraint = constraint
        self.relaxed_bound = None

    def implement(self):
        self.constraint.relaxed_bound = self.relaxed_bound

    def pretty_print(self):
        cost = -1 * abs(self.relaxed_bound - self.constraint.risk_bound) * self.constraint.relax_cost
        print(self.constraint.name + ": " + str(self.constraint.risk_bound) +" -> "+str(self.relaxed_bound) + " (" +str(cost)+ ")")


