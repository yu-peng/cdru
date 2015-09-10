__author__ = 'yupeng'

class Assignment(object):

    def __init__(self, decision_variable, value, utility):
        self.decision_variable = decision_variable
        self.value = value
        self.utility = utility

    def __lt__(self, other):
        return self.utility > other.utility

    def pretty_print(self):
        print(self.decision_variable.name + " <- "+ self.value +" ("+str(self.utility)+")")