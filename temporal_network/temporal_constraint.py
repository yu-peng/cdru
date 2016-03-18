__author__ = 'yupeng'


class TemporalConstraint(object):

    def __init__(self, id, name, fro, to, lower_bound, upper_bound):
        self.id = id
        self.name = name
        self.fro = fro
        self.to = to
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.guards = set()
        self.controllable = True

        self.activated = False
        self.relaxed_lb = None
        self.relaxed_ub = None

        self.relaxable_lb = False
        self.relaxable_ub = False

        self.relax_cost_lb = 0.01
        self.relax_cost_ub = 0.01

    def add_guard(self,guard):
        self.guards.add(guard)

    def get_lower_bound(self):
        if self.relaxed_lb is None:
            return self.lower_bound
        else:
            return self.relaxed_lb

    def get_upper_bound(self):
        if self.relaxed_ub is None:
            return self.upper_bound
        else:
            return self.relaxed_ub

    def pretty_print(self):

        expression_str = []

        expression_str.append('(%s:%s->%s)[%.4f,%.4f]' % (self.name, self.fro, self.to, self.lower_bound, self.upper_bound))

        print(''.join(expression_str))
