__author__ = 'yupeng'

from queue import PriorityQueue
import json

class Candidate(object):

    def __init__(self):
        self.assignments = set()
        self.temporal_relaxations = set()
        self.utility = 0

        self.resolved_conflicts = set()
        self.continuously_resolved_cycles = set()
        self.assignments_to_avoid = set()

        self.assigned_variables = set()
        self.unassigned_variables = PriorityQueue()

        self.semantic_relaxations = set()

    def __lt__(self, other):
        return self.utility > other.utility

    def add_assignment(self,new_assignment):

        # if its guard is in conflict with existing assignments, return false
        if not self.add_guard_assignments(new_assignment.decision_variable.guards):
            return False

        # Check if this assignment is in the 'assignments_to_avoid' set
        if new_assignment in self.assignments_to_avoid:
            return False

        # TODO: check if this assignment itself is in conflict with any existing assignment
        # How to do it efficiently????
        for existing_assignment in self.assignments:
            if existing_assignment.decision_variable is new_assignment.decision_variable:
                if not existing_assignment is new_assignment:
                    return False


        self.assignments.add(new_assignment)
        self.utility += new_assignment.utility
        self.assigned_variables.add(new_assignment.decision_variable)

        return True

    def add_assignments(self,new_assignments):
        for new_assignment in new_assignments:
            if not self.add_assignment(new_assignment):
                return False

        return True

    def add_temporal_relaxation(self,new_relaxation):

        # check if the guard of this relaxation is in conflict with any existing assignment
        if not self.add_guard_assignments(new_relaxation.constraint.guards):
            return False

        self.temporal_relaxations.add(new_relaxation)
        if new_relaxation.relaxed_lb is not None:
            self.utility -= abs(new_relaxation.relaxed_lb - new_relaxation.constraint.lower_bound) * new_relaxation.constraint.relax_cost_lb

        if new_relaxation.relaxed_ub is not None:
            self.utility -= abs(new_relaxation.relaxed_ub - new_relaxation.constraint.upper_bound) * new_relaxation.constraint.relax_cost_ub

        return True

    def add_temporal_relaxations(self,new_relaxations):
        for new_relaxation in new_relaxations:
            if not self.add_temporal_relaxation(new_relaxation):
                return False

        return True

    def add_semantic_relaxation(self, semantic_relaxation):
        self.semantic_relaxations.add(semantic_relaxation)

    def add_semantic_relaxations(self, semantic_relaxations):
        for semantic_relaxation in semantic_relaxations:
            self.add_semantic_relaxation(semantic_relaxation)

    def add_guard_assignments(self,guards):
        for guard in guards:
            if not self.add_assignment(guard):
                return False
            if not self.add_guard_assignments(guard.decision_variable.guards):
                return False

        return True

    def pretty_print(self):
        print("Candidate ("+ str(self.utility) +")")

        print("Assignment# "+ str(len(self.assignments)) +"  Relaxation# " + str(len(self.temporal_relaxations)))
        print("Resolved Conflict# "+ str(len(self.resolved_conflicts)) +"  Cont Resolved# " + str(len(self.continuously_resolved_cycles)))
        print("Assignment To Avoid# "+ str(len(self.assignments_to_avoid)) +"  Unassigned Var# " + str(self.unassigned_variables.qsize()))

        for assignment in self.assignments:
            assignment.pretty_print()

        for relaxation in self.temporal_relaxations:
            relaxation.pretty_print()

        for relaxation in self.semantic_relaxations:
            relaxation.pretty_print()

    def json_print(self,problemName,solverName,runTime):
        result = {}

        result['TestName'] = problemName
        result['Solver'] = solverName
        result['Runtime'] = runTime

        result['Utility'] = self.utility

        assignmentsObj = []
        for assignment in self.assignments:
            assignmentObj = {}
            assignmentObj['Variable'] = assignment.decision_variable.name
            assignmentObj['Value'] = assignment.value
            assignmentObj['Utility'] = assignment.utility
            assignmentsObj.append(assignmentObj)

        if len(assignmentsObj) > 0:
            result['Assignments'] = assignmentsObj

        relaxationsObj = []
        for relaxation in self.temporal_relaxations:
            relaxationObj = {}
            relaxationObj['ConstraintID'] = relaxation.constraint.id

            if relaxation.relaxed_ub is not None:
                relaxationObj['Bound'] = "UB"
                relaxationObj['OriginalValue'] = relaxation.constraint.upper_bound
                relaxationObj['RelaxedValue'] = relaxation.relaxed_ub

            if relaxation.relaxed_lb is not None:
                relaxationObj['Bound'] = "LB"
                relaxationObj['OriginalValue'] = relaxation.constraint.lower_bound
                relaxationObj['RelaxedValue'] = relaxation.relaxed_lb

            relaxationsObj.append(relaxationObj)

        if len(relaxationsObj) > 0:
            result['Relaxations'] = relaxationsObj

        return json.dumps(result)