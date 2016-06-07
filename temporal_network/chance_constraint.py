__author__ = 'yupeng'


class ChanceConstraint(object):

    def __init__(self, id, name, risk_bound):
        self.id = id
        self.name = name
        self.risk_bound = risk_bound
        self.relaxed_bound = None
        self.relaxable_bound = False
        self.relax_cost = 0.01


    def get_bound(self):
        if self.relaxed_bound is None:
            return self.risk_bound
        else:
            return self.relaxed_bound


    def pretty_print(self):

        expression_str = []

        expression_str.append('(%s:)[%.4f]' % (self.name, self.risk_bound))

        print(''.join(expression_str))
