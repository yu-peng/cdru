__author__ = 'yupeng'

from scipy.stats import norm, truncnorm


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

        a,b = (0-self.constraint.mean)/self.constraint.std,(1e6-self.constraint.mean)/self.constraint.std

        ub_survival = truncnorm.sf(self.allocated_ub, a,b,loc=self.constraint.mean, scale=self.constraint.std)
        lb_mass = truncnorm.cdf(self.allocated_lb, a,b,loc=self.constraint.mean, scale=self.constraint.std)

        print(self.constraint.name + ": [" + str(self.allocated_lb) + "," + str(
                self.allocated_ub) + "] (Risk: " + str(lb_mass+ub_survival) + ")")

