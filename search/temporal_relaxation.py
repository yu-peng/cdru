__author__ = 'yupeng'


class TemporalRelaxation(object):

    def __init__(self, constraint):
        self.constraint = constraint
        self.relaxed_lb = None
        self.relaxed_ub = None

    def implement(self):
        if self.relaxed_lb is not None:
            self.constraint.relaxed_lb = self.relaxed_lb

        if self.relaxed_ub is not None:
            self.constraint.relaxed_ub = self.relaxed_ub

    def pretty_print(self):
        if self.relaxed_lb is not None:
            print(self.constraint.name + "(LB): "+ str(self.constraint.lower_bound) +" -> "+str(self.relaxed_lb))

        if self.relaxed_ub is not None:
            print(self.constraint.name + "(UB): "+ str(self.constraint.upper_bound) +" -> "+str(self.relaxed_ub))


