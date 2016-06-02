__author__ = 'yupeng'


class TemporalAllocation(object):

    def __init__(self, constraint):
        self.constraint = constraint
        self.allocated_lb = None
        self.allocated_ub = None

    def implement(self):
        if self.allocated_lb is not None:
            self.constraint.relaxed_lb = self.allocated_lb

        if self.allocated_ub is not None:
            self.constraint.relaxed_ub = self.allocated_ub

    def pretty_print(self):
        if self.allocated_lb is not None:
            print(self.constraint.name + "(LB): "+ str(self.allocated_lb))

        if self.allocated_ub is not None:
            print(self.constraint.name + "(UB): "+ str(self.allocated_ub))


