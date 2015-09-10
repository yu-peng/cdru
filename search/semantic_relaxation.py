__author__ = 'yupeng'

class SemanticRelaxation(object):

    # Semantic relaxation

    def __init__(self, decision_variable, domain_value):
        self.decision_variable = decision_variable
        self.additional_domain_value = domain_value

    def pretty_print(self):
        print(self.decision_variable.name + " <-- " + self.additional_domain_value)