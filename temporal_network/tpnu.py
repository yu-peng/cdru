__author__ = 'yupeng'

from temporal_network.temporal_constraint import TemporalConstraint
from temporal_network.decision_variable import DecisionVariable
from temporal_network.assignment import Assignment
import xml.etree.ElementTree

class Tpnu(object):

    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.num_nodes = 0
        self.decision_variables = {}
        self.temporal_constraints = {}
        self.node_number_to_id = {}

    def add_decision_variable(self, variable):
        self.decision_variables[variable.id] = variable

    def add_temporal_constraint(self, constraint):
        self.temporal_constraints[constraint.id] = constraint

    def initialize(self):

        # make any unconditional temporal constraints
        # active
        for constraint in self.temporal_constraints.values():
            if len(constraint.guards) == 0:
                constraint.activated = True

    @staticmethod
    def isCCTP(inFilename):
        e = xml.etree.ElementTree.parse(inFilename).getroot()
        if "CCTP" in e.tag:
            return True

        return False

    @staticmethod
    def isTPN(inFilename):
        e = xml.etree.ElementTree.parse(inFilename).getroot()
        if "tpn" in e.tag:
            return True

        return False

    @staticmethod
    def parseCCTP(inFilename):
        e = xml.etree.ElementTree.parse(inFilename).getroot()

        tpnu_name = e.find('NAME').text
        tpnu = Tpnu('', tpnu_name)

        # In TPN format every node (or event in TPN terminology) has a non-unique name
        # and an unique id. Both of those are strings. For efficiency DC checking algorithms
        # denote each node by a number, such that we can cheaply check their equality.

        # parse the event
        event_ids = set()
        tpnu.node_id_to_name = {}
        tpnu.node_number_to_id = {}
        tpnu.node_id_to_number = {}

        for event_obj in e.findall('EVENT'):
            eid, ename = event_obj.find('ID').text, event_obj.find('NAME').text
            event_ids.add(eid)
            tpnu.node_id_to_name[eid] = ename

        for eid in event_ids:
            next_number = len(tpnu.node_number_to_id) + 1
            tpnu.node_number_to_id[next_number] = eid
            tpnu.node_id_to_number[eid] = next_number

        tpnu.num_nodes = len(tpnu.node_number_to_id)

        if (tpnu.num_nodes < 1):
            return None

        # parse the decision variables
        assignment_map_with_id = {}
        assignment_map_with_name = {}

        for variable_obj in e.findall('DECISION-VARIABLE'):
            dv_name = variable_obj.find('DECISION-NAME').text

            if variable_obj.find('ID') is not None:
                dv_id = variable_obj.find('ID').text
            else:
                dv_id = dv_name

            decision_variable = DecisionVariable(dv_id,dv_name)

            # construct the assignment for the variable
            for value_obj in variable_obj.findall('VALUE'):
                # value_id = value_obj.find('ID').text
                value_name = value_obj.find('VALUE-NAME').text
                value_utility = float(value_obj.find('VALUE-UTILITY').text)
                assignment = Assignment(decision_variable, value_name, value_utility)

                # add the assignment to the variable, and a dictionary for future reference
                decision_variable.add_domain_value(assignment)

                # using the id of the variable and the value of the assignment as key
                assignment_map_with_id[(dv_id,value_name)] = assignment
                assignment_map_with_name[(dv_name,value_name)] = assignment

            tpnu.add_decision_variable(decision_variable)

        # parse variables' guards
        for variable_obj in e.findall('DECISION-VARIABLE'):

            if variable_obj.find('ID') is not None:
                dv_id = variable_obj.find('ID').text
            else:
                dv_id = variable_obj.find('DECISION-NAME').text

            decision_variable = tpnu.decision_variables[dv_id]

            # the guard could be a conjunctive set of assignment

            for guard_obj in variable_obj.findall('GUARD'):
                # guard_id = guard_obj.find('ID').text
                guard_variable = guard_obj.find('GUARD-VARIABLE').text
                guard_value = guard_obj.find('GUARD-VALUE').text

                # retrieve the assignment
                if (guard_variable,guard_value) in assignment_map_with_id:
                    guard_assignment = assignment_map_with_id[(guard_variable,guard_value)]
                elif (guard_variable,guard_value) in assignment_map_with_name:
                    guard_assignment = assignment_map_with_name[(guard_variable,guard_value)]
                # and add to the guards of this decision variable
                decision_variable.add_guard(guard_assignment)


        # parse the temporal constraints and episodes

        # if line below confuses you, that's expected... We need better automated code generation for parsing...
        for constraint_obj in e.findall('CONSTRAINT'):
            # duration can be one of three types - controllable, uncertain and probabilistic
            # here we are only handling the first two cases, which are sorted into two lists
            # in our resulting stnu class.

            lower_bound = float(constraint_obj.find('LOWERBOUND').text)
            upper_bound = float(constraint_obj.find('UPPERBOUND').text)

            from_event = constraint_obj.find('START').text
            to_event = constraint_obj.find('END').text
            constraint_id = constraint_obj.find('ID').text
            constraint_name = constraint_obj.find('NAME').text

            constraint = TemporalConstraint(constraint_id, constraint_name, tpnu.node_id_to_number[from_event], tpnu.node_id_to_number[to_event], lower_bound, upper_bound)

            # check if the constraint is controllable and relaxable
            type = constraint_obj.find('TYPE').text

            if "Controllable" in type:
                constraint.controllable = True
            elif "Uncontrollable" in type:
                constraint.controllable = False

            if constraint_obj.find('LBRELAXABLE') is not None:
                if "T" in constraint_obj.find('LBRELAXABLE').text:
                    constraint.relaxable_lb = True
                    lb_cost = constraint_obj.find('LB-RELAX-COST-RATIO').text
                    constraint.relax_cost_lb = float(lb_cost)

            if constraint_obj.find('UBRELAXABLE') is not None:
                if "T" in constraint_obj.find('UBRELAXABLE').text:
                    constraint.relaxable_ub = True
                    ub_cost = constraint_obj.find('UB-RELAX-COST-RATIO').text
                    constraint.relax_cost_ub = float(ub_cost)

            # Next we deal with the guard conditions
            # the approach is identical to that for decision variables

            for guard_obj in constraint_obj.findall('GUARD'):
                # guard_id = guard_obj.find('ID').text
                guard_variable = guard_obj.find('GUARD-VARIABLE').text
                guard_value = guard_obj.find('GUARD-VALUE').text

                # retrieve the assignment
                if (guard_variable,guard_value) in assignment_map_with_id:
                    guard_assignment = assignment_map_with_id[(guard_variable,guard_value)]
                elif (guard_variable,guard_value) in assignment_map_with_name:
                    guard_assignment = assignment_map_with_name[(guard_variable,guard_value)]
                # and add to the guards of this decision variable
                constraint.add_guard(guard_assignment)



            tpnu.add_temporal_constraint(constraint)

        return tpnu


    @staticmethod
    def writeCCTP(tpnu, outFilename):
        f = open(outFilename, 'w')
        f.write("""<?xml version="1.0" encoding="UTF-8"?>\r""")
        tpnu.export(f,0)
        f.close()

    @staticmethod
    def from_tpn_autogen(tpn):

        tpn_id = tpn.get_id()
        tpn_name = tpn.get_name()

        tpnu = Tpnu(tpn_id, tpn_name)

        # In TPN format every node (or event in TPN terminology) has a non-unique name
        # and an unique id. Both of those are strings. For efficiency DC checking algorithms
        # denote each node by a number, such that we can cheaply check their equality.

        # parse the event

        event_ids = set()
        tpnu.node_id_to_name = {}
        tpnu.node_number_to_id = {}
        tpnu.node_id_to_number = {}

        for event in tpn.get_events().get_event():
            eid, ename = event.get_id(), event.get_name()
            event_ids.add(eid)
            tpnu.node_id_to_name[eid] = ename

        for eid in event_ids:
            next_number = len(tpnu.node_number_to_id) + 1
            tpnu.node_number_to_id[next_number] = eid
            tpnu.node_id_to_number[eid] = next_number

        tpnu.num_nodes = len(tpnu.node_number_to_id)

        assignment_map = {}
        # parse the decision variables
        for tpn_dv in tpn.get_decision_variables().get_decision_variable():
            dv_id = tpn_dv.get_id()
            dv_name = tpn_dv.get_name()
            decision_variable = DecisionVariable(dv_id,dv_name)

            # construct the assignment for the variable
            for domain_value in tpn_dv.get_domain().get_domainval():
                value_name = domain_value.get_value()
                value_utility = domain_value.get_utility()
                assignment = Assignment(decision_variable, value_name, value_utility)

                # add the assignment to the variable, and a dictionary for future reference
                decision_variable.add_domain_value(assignment)

                # using the id of the variable and the value of the assignment as key
                assignment_map[(dv_id,value_name)] = assignment

            tpnu.add_decision_variable(decision_variable)

        # parse their guards
        for tpn_dv in tpn.get_decision_variables().get_decision_variable():
            dv_id = tpn_dv.get_id()
            decision_variable = tpnu.decision_variables[dv_id]

            # the guard could be a single value
            # or a conjunctive set of assignment
            single_guard = tpn_dv.get_guard().get_decision_variable_equals()
            guard_list = tpn_dv.get_guard().get_and()

            if single_guard is not None:
                guard_variable_id = single_guard.get_variable()
                guard_value = single_guard.get_value()

                # retrieve the assignment
                guard_assignment = assignment_map[(guard_variable_id,guard_value)]
                # and add to the guards of this decision variable
                decision_variable.add_guard(guard_assignment)

            if guard_list is not None:
                for guard in guard_list.get_guard():
                    guard_variable_id = guard.get_decision_variable_equals().get_variable()
                    guard_value = guard.get_decision_variable_equals().get_value()

                    # retrieve the assignment
                    guard_assignment = assignment_map[(guard_variable_id,guard_value)]
                    # and add to the guards of this decision variable
                    decision_variable.add_guard(guard_assignment)


        # parse the temporal constraints and episodes

        # if line below confuses you, that's expected... We need better automated code generation for parsing...
        for temporal_constraint in tpn.get_temporal_constraints().get_temporal_constraint() + tpn.get_episodes().get_episode():
            # duration can be one of three types - controllable, uncertain and probabilistic
            # here we are only handling the first two cases, which are sorted into two lists
            # in our resulting stnu class.

            controllable_duration = temporal_constraint.get_duration().get_bounded_duration()
            uncertain_duration = temporal_constraint.get_duration().get_set_bounded_uncertain_duration()


            duration = controllable_duration or uncertain_duration
            lower_bound = duration.get_lower_bound()
            upper_bound = duration.get_upper_bound()
            from_event = temporal_constraint.get_from_event()
            to_event = temporal_constraint.get_to_event()
            constraint_id = temporal_constraint.get_id()
            constraint_name = temporal_constraint.get_name()
            constraint = TemporalConstraint(constraint_id, constraint_name, tpnu.node_id_to_number[from_event], tpnu.node_id_to_number[to_event], lower_bound, upper_bound)

            if controllable_duration is not None:
                constraint.controllable = True
                constraint.relaxable_ub = True

            elif uncertain_duration is not None:
                constraint.controllable = False

            # Next we deal with the guard conditions
            # the approach is identical to that for decision variables

            # the guard could be a single value
            # or a conjunctive set of assignment
            single_guard = temporal_constraint.get_guard().get_decision_variable_equals()
            guard_list = temporal_constraint.get_guard().get_and()

            if single_guard is not None:
                guard_variable_id = single_guard.get_variable()
                guard_value = single_guard.get_value()

                # retrieve the assignment
                guard_assignment = assignment_map[(guard_variable_id,guard_value)]
                # and add to the guards of this decision variable
                constraint.add_guard(guard_assignment)

            if guard_list is not None:
                for guard in guard_list.get_guard():
                    guard_variable_id = guard.get_decision_variable_equals().get_variable()
                    guard_value = guard.get_decision_variable_equals().get_value()

                    # retrieve the assignment
                    guard_assignment = assignment_map[(guard_variable_id,guard_value)]
                    # and add to the guards of this decision variable
                    constraint.add_guard(guard_assignment)

            tpnu.add_temporal_constraint(constraint)

        return tpnu