__author__ = 'yupeng'

from queue import PriorityQueue
import json

class Candidate(object):

    def __init__(self):
        self.assignments = set()
        self.temporal_relaxations = set()
        self.temporal_allocations = set()
        self.chance_constraint_relaxations = set()
        self.g = 0 # reward/cost so far
        self.h = 0 # max reward/min cost to go

        self.resolved_conflicts = set()
        self.continuously_resolved_cycles = set()
        self.assignments_to_avoid = set()

        self.assigned_variables = set()
        self.unassigned_variables = PriorityQueue()

        self.semantic_relaxations = set()

    def __lt__(self, other):
        return (self.g + self.h) > (other.g + other.h)

    def add_assignment(self,new_assignment):

        if new_assignment in self.assignments:
            return True

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
        self.g += new_assignment.utility
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
            self.g -= abs(new_relaxation.relaxed_lb - new_relaxation.constraint.lower_bound) * new_relaxation.constraint.relax_cost_lb

        if new_relaxation.relaxed_ub is not None:
            self.g -= abs(new_relaxation.relaxed_ub - new_relaxation.constraint.upper_bound) * new_relaxation.constraint.relax_cost_ub

        return True

    def add_temporal_relaxations(self,new_relaxations):
        for new_relaxation in new_relaxations:
            if not self.add_temporal_relaxation(new_relaxation):
                return False

        return True

    def add_temporal_allocation(self,new_allocation):

        # check if the guard of this relaxation is in conflict with any existing assignment
        if not self.add_guard_assignments(new_allocation.constraint.guards):
            return False

        self.temporal_allocations.add(new_allocation)

        return True

    def add_temporal_allocations(self,new_allocations):
        for new_allocation in new_allocations:
            if not self.add_temporal_allocation(new_allocation):
                return False

        return True

    def add_semantic_relaxation(self, semantic_relaxation):
        self.semantic_relaxations.add(semantic_relaxation)

    def add_semantic_relaxations(self, semantic_relaxations):
        for semantic_relaxation in semantic_relaxations:
            self.add_semantic_relaxation(semantic_relaxation)

    def add_chance_constraint_relaxation(self,new_relaxation):
        self.chance_constraint_relaxations.add(new_relaxation)
        self.g -= abs(new_relaxation.relaxed_bound - new_relaxation.constraint.risk_bound) * new_relaxation.constraint.relax_cost

    def add_chance_constraint_relaxations(self,new_relaxations):
        for new_relaxation in new_relaxations:
            self.add_chance_constraint_relaxation(new_relaxation)

        return True

    def add_guard_assignments(self,guards):
        for guard in guards:
            if not self.add_assignment(guard):
                return False
            if not self.add_guard_assignments(guard.decision_variable.guards):
                return False

        return True

    def pretty_print(self):
        print("Candidate (" + str(self.g) + "/" + str(self.h) + ")")

        print("Assignment# "+ str(len(self.assignments)) +"  Relaxation# " + str(len(self.temporal_relaxations))+"  Allocation# " + str(len(self.temporal_allocations)))
        print("Resolved Conflict# "+ str(len(self.resolved_conflicts)) +"  Cont Resolved# " + str(len(self.continuously_resolved_cycles)))
        print("Assignment To Avoid# "+ str(len(self.assignments_to_avoid)) +"  Unassigned Var# " + str(self.unassigned_variables.qsize()))

        for assignment in self.assignments:
            assignment.pretty_print()

        for relaxation in self.temporal_relaxations:
            relaxation.pretty_print()

        for allocation in self.temporal_allocations:
            allocation.pretty_print()

        for relaxation in self.chance_constraint_relaxations:
            relaxation.pretty_print()

        for relaxation in self.semantic_relaxations:
            relaxation.pretty_print()

    def json_print(self,problemName,solverName,runTime,candidates):

        return json.dumps(self.json_description(problemName,solverName,runTime,candidates))

    def json_description(self,problemName,solverName,runTime,candidates):
        result = {}

        result["TestName"] = problemName
        result["Solver"] = solverName
        result["Runtime"] = runTime

        result["Utility"] = self.g
        result["Candidates"] = candidates
        result["Conflicts"] = len(self.resolved_conflicts)

        assignmentsObj = []
        for assignment in self.assignments:
            assignmentObj = {}
            assignmentObj["Variable"] = assignment.decision_variable.id
            assignmentObj["Value"] = assignment.value
            assignmentObj["Utility"] = assignment.utility
            assignmentsObj.append(assignmentObj)

        if len(assignmentsObj) > 0:
            result["Assignments"] = assignmentsObj

        relaxationsObj = []
        for relaxation in self.temporal_relaxations:
            relaxationObj = {}
            relaxationObj["ConstraintID"] = relaxation.constraint.id
            relaxationObj["ConstraintName"] = relaxation.constraint.name

            if relaxation.relaxed_ub is not None:
                relaxationObj["Bound"] = "UB"
                relaxationObj["OriginalValue"] = relaxation.constraint.upper_bound
                relaxationObj["RelaxedValue"] = relaxation.relaxed_ub

            if relaxation.relaxed_lb is not None:
                relaxationObj["Bound"] = "LB"
                relaxationObj["OriginalValue"] = relaxation.constraint.lower_bound
                relaxationObj["RelaxedValue"] = relaxation.relaxed_lb

            relaxationsObj.append(relaxationObj)

        if len(relaxationsObj) > 0:
            result["Relaxations"] = relaxationsObj

        allocationsObj = []
        for allocation in self.temporal_allocations:
            allocationObj = {}
            allocationObj["ConstraintID"] = allocation.constraint.id
            allocationObj["ConstraintName"] = allocation.constraint.name

            allocationObj["AllocatedLB"] = allocation.allocated_lb
            allocationObj["AllocatedUB"] = allocation.allocated_ub

            allocationsObj.append(allocationObj)

        if len(allocationsObj) > 0:
            result["Allocations"] = allocationsObj

        cc_relaxationsObj = []
        for relaxation in self.chance_constraint_relaxations:
            relaxationObj = {}
            relaxationObj["ConstraintID"] = relaxation.constraint.id
            relaxationObj["ConstraintName"] = relaxation.constraint.name

            if relaxation.relaxed_bound is not None:
                relaxationObj["OriginalValue"] = relaxation.constraint.risk_bound
                relaxationObj["RelaxedValue"] = relaxation.relaxed_bound

                cc_relaxationsObj.append(relaxationObj)

        if len(cc_relaxationsObj) > 0:
            result["CCRelaxations"] = cc_relaxationsObj

        return result