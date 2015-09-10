__author__ = 'yupeng'

class DecisionVariable(object):

    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.domain = set()
        self.guards = set()

        self.optimal_utility = 0

    def __lt__(self, other):
        return self.optimal_utility > other.optimal_utility

    def add_domain_value(self,value):
        self.domain.add(value)

    def add_guard(self,guard):
        self.guards.add(guard)