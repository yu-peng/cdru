__author__ = 'yupeng'

from controllability.strong_controllability import StrongControllability
from controllability.temporal_consistency import TemporalConsistency

from queue import PriorityQueue
from search.candidate import Candidate
from controllability.dynamic_controllability import DynamicControllability
from search.conflict import Conflict
from search.maxflex_relaxation import MaxFlexRelaxation
from search.mincost_relaxation import MinCostRelaxation
from temporal_network.tpnu import FeasibilityType, ObjectiveType, ChanceConstrained


class SearchProblem(object):

    def __init__(self, tpnu, f_type, o_type, c_type):
        self.tpnu = tpnu
        self.queue = PriorityQueue()
        self.known_conflicts = set()
        self.feasibility_type = f_type
        self.objective_type = o_type
        self.chance_constrained = c_type

        self.candidates_dequeued = 0;

        if self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
            # Preprocess the uncontrollable durations in the tpnu
            # by setting the upper bounds of them to a very large number

            for key in self.tpnu.temporal_constraints:
                constraint = self.tpnu.temporal_constraints[key]
                if not constraint.controllable:
                    constraint.upper_bound = 100000

        if self.chance_constrained == ChanceConstrained.ON:
            # Retrieve the only chance constraint
            for key in self.tpnu.chance_constraints:
                constraint = self.tpnu.chance_constraints[key]
                self.cc = constraint

            # initialize the bound of probabilistic durations to +- 6 sigma
            for key in self.tpnu.temporal_constraints:
                constraint = self.tpnu.temporal_constraints[key]
                if not constraint.controllable and constraint.probabilistic:
                    # print("Initializing " + constraint.name)
                    constraint.upper_bound = constraint.mean + 6*constraint.std
                    constraint.lower_bound = max(0,constraint.mean - 6*constraint.std)


    def initialize(self):
        # clear the search state
        self.queue = PriorityQueue()
        self.known_conflicts = set()

        # make any unconditional temporal constraints
        # active
        for constraint in self.tpnu.temporal_constraints.values():
            if len(constraint.guards) == 0:
                constraint.activated = True
            else:
                constraint.activated = False

        # add an empty candidate to the queue
        first_candidate = Candidate()

        # make any unconditional decision variables
        # available for assignment
        for variable in self.tpnu.decision_variables.values():
            if len(variable.guards) == 0:
                first_candidate.unassigned_variables.put(variable)

        self.queue.put(first_candidate)

        # initialize the heuristic for each decision variable
        for dv in self.tpnu.decision_variables.values():
            self.update_variable_heuristics(dv)

    def update_variable_heuristics(self,variable):
        # get the domain assignment with the highest reward
        best_domain_assignment = sorted(list(variable.domain),key=lambda assignment: assignment.utility, reverse=True)[0]
        if best_domain_assignment.utility > variable.optimal_utility:
            variable.optimal_utility = best_domain_assignment.utility

        # propagate it to the parent
        for guard_assignment in variable.guards:
            guard_variable = guard_assignment.decision_variable
            if guard_variable.optimal_utility < guard_assignment.utility + variable.optimal_utility:
                guard_variable.optimal_utility = guard_assignment.utility + variable.optimal_utility
                self.update_variable_heuristics(guard_variable)

    def next_solution(self):

        # if the search queue is empty
        # no more solution can be found
        while not self.queue.empty():

            # dequeue the current candidate
            candidate = self.queue.get()
            self.candidates_dequeued += 1
            # print(str(self.candidates_dequeued) + "\t" + str(candidate.f))

            # print("Dequeue candidate: " + str(candidate.f) + "/" + str(candidate.g) + "\n")
            # candidate.pretty_print()

            # check if it has resolved all conflicts
            # unresolved_conflict = None
            # if self.check_complete(candidate) is None:
            unresolved_conflict = self.check_conflict_resolution(candidate)

            # if not, get an unresolved conflict and expand on it
            if unresolved_conflict is not None:
                self.expand_on_conflict(candidate,unresolved_conflict)
            else:

                # if yes, check if it is complete
                unassigned_variable = self.check_complete(candidate)

                if unassigned_variable is not None:

                    # if incomplete, get an unassigned variable and expand on it
                    self.expand_on_variable(candidate,unassigned_variable)

                else:
                    # if complete, check if it is consistent
                    new_conflict = self.consistent(candidate)

                    if new_conflict is not None:
                        # new_conflict.pretty_print()
                        # if (len(new_conflict.negative_cycles) > 1):
                        #     break
                        # if inconsistent, extract and record a conflict,
                        self.known_conflicts.add(new_conflict)
                        # print("new conflict: " + str(len(self.known_conflicts)));
                        # and put the back to the queue
                        self.add_candidate_to_queue(candidate)

                    else:
                        # if consistent, return the candidate as a feasible solution

                        if self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
                            maxFlex = 99999
                            self.implement(candidate)
                            for id in self.tpnu.temporal_constraints:
                                constraint = self.tpnu.temporal_constraints[id]
                                if not constraint.controllable:
                                    if constraint.get_upper_bound() - constraint.get_lower_bound() < maxFlex:
                                        maxFlex = constraint.get_upper_bound() - constraint.get_lower_bound()

                            candidate.utility = maxFlex
                        return candidate

        return None

    def check_conflict_resolution(self,candidate):

        # check against the list of known conflicts
        # and see if the candidate can resolve it

        # TODO: add in more efficient code for conflict detection

        unresolved_conflicts = self.known_conflicts.difference(candidate.resolved_conflicts)
        for unresolved_conflict in unresolved_conflicts:
            # check if there is one assignment in the candidate that
            # negates one assignment in the conflict

            resolved = False
            for candidate_assignment in candidate.assignments:
                for conflict_assignment in unresolved_conflict.assignments:

                    if not resolved:
                        # first, find the assignments that share the same decision variable
                        if candidate_assignment.decision_variable is conflict_assignment.decision_variable:
                            if candidate_assignment is not conflict_assignment:
                                # next, if they are different, meaning that this conflict is resolved
                                resolved = True

                                # add to the candidate's resolved conflict
                                candidate.resolved_conflicts.add(unresolved_conflict)

                                # and move on to the next conflict
                                break

            # otherwise, we return this as an unresolved conflict
            if not resolved:
                return unresolved_conflict

        return None

    def expand_on_conflict(self,candidate,conflict):

        # extend the candidate using the resolutions to the
        # conflict

        # will do two types of expansions using both
        # discrete and continuous relaxations

        # discrete resolution

        # print("Expanding on conflict")
        # conflict.pretty_print()

        found_discrete_relaxation = False

        conflict_assignments = conflict.assignments.copy()
        while len(conflict_assignments) > 0:

            conflict_assignment = conflict_assignments.pop()

            # take the negation of this conflict
            for alternative_assignment in conflict_assignment.decision_variable.domain:
                if not alternative_assignment is conflict_assignment:
                    # create a new candidate

                    # print("Extending candidate ")
                    # candidate.pretty_print()
                    # print("with alternative ")
                    # alternative_assignment.pretty_print()

                    new_candidate = self.create_child_candidate_from_assignment(candidate,alternative_assignment)

                    # add the newly created candidates to the
                    # queue
                    if new_candidate is not None:
                        # add assignments to avoid
                        new_candidate.assignments_to_avoid.update(conflict_assignments)
                        new_candidate.resolved_conflicts.add(conflict)

                        self.add_candidate_to_queue(new_candidate)
                        found_discrete_relaxation = True

        # TODO: add in the actual code for expand on conflict,
        # TODO: do not forget to add the guard for all new assignment or relaxation
        # TODO: and update the available variable list
        # TODO: and make sure that assignment_to_avoid is set properly


        # continuous resolution
        # we compute one optimal continuous relaxation
        # for each of the negative cycle in the conflict
        # subject to all continuously resolved conflict before
        for negative_cycle in conflict.negative_cycles:

            # construct a LP to solve for this problem
            # the constraints are all previous negative cycles
            # plus this new one
            self.implement(candidate)
            if self.objective_type == ObjectiveType.MIN_COST:
                if self.chance_constrained == ChanceConstrained.ON:
                    try:
                        from search.mincost_cc_relaxation import ChanceConstrainedRelaxation
                    except ImportError:
                        # pass # Gurobi doesn't exist, use default Pulp solver.
                        raise Exception("Missing subsolvers on this system for chance-constrained relaxation. Check if you have scipy and snopt installed correctly.")

                    relaxations, allocations, cc_relaxations, utility = ChanceConstrainedRelaxation.generate_cc_relaxations(candidate,
                                                                                               negative_cycle,self.feasibility_type,self.cc)
                    if relaxations is not None or allocations is not None:
                        # we construct new candidates using the relaxations and allocations
                        new_candidate = self.create_child_candidate_from_relaxations(candidate, relaxations=relaxations, allocations=allocations)
                        if new_candidate is not None:
                            if cc_relaxations is not None:
                                new_candidate.add_chance_constraint_relaxations(cc_relaxations)
                            new_candidate.resolved_conflicts.add(conflict)
                            new_candidate.continuously_resolved_cycles.add(negative_cycle)
                            self.add_candidate_to_queue(new_candidate)
                else:
                    relaxations,utility = MinCostRelaxation.generate_mincost_relaxations(candidate,negative_cycle,self.feasibility_type)
                    if relaxations is not None:
                        # we construct new candidates using this relaxations
                        new_candidate = self.create_child_candidate_from_relaxations(candidate,relaxations=relaxations)
                        if new_candidate is not None:
                            new_candidate.resolved_conflicts.add(conflict)
                            new_candidate.continuously_resolved_cycles.add(negative_cycle)
                            self.add_candidate_to_queue(new_candidate)

            elif self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
                relaxations,max_flex_value = MaxFlexRelaxation.generate_maxflex_relaxations(candidate,negative_cycle)
                if relaxations is not None:
                    # we construct new candidates using this relaxations
                    new_candidate = self.create_child_candidate_from_relaxations(candidate,relaxations=relaxations)
                    if new_candidate is not None:
                        new_candidate.resolved_conflicts.add(conflict)
                        new_candidate.continuously_resolved_cycles.add(negative_cycle)
                        # Override the utility to reflex the max-flexibility enabled by this candidate
                        new_candidate.g = max_flex_value
                        # print("New flex value: " + str(new_candidate.f))
                        # new_candidate.pretty_print()
                        self.add_candidate_to_queue(new_candidate)
            else:
                raise Exception("Unknown objective type: " + str(self.objective_type))




    def check_complete(self,candidate):

        # check if no available variable left
        # that is unassigned

        if candidate.unassigned_variables.empty():
            return None
        else:
            # get an unassigned variable
            # with the highest expected utility
            variable = candidate.unassigned_variables.queue[0]
            # candidate.unassigned_variables.put(variable)
            return variable


    def expand_on_variable(self,candidate,variable):

        # expand the candidate using the
        # assignments to the variable
        for domain_assignment in variable.domain:

            # create a new candidate
            new_candidate = self.create_child_candidate_from_assignment(candidate,domain_assignment)

            # add the newly created candidates to the
            # queue
            if new_candidate is not None:
                self.add_candidate_to_queue(new_candidate)

    def create_child_candidate_from_assignment(self,candidate,assignment):

        new_candidate = Candidate()

        new_candidate.resolved_conflicts = candidate.resolved_conflicts.copy()
        new_candidate.continuously_resolved_cycles = candidate.continuously_resolved_cycles.copy()
        new_candidate.assignments_to_avoid = candidate.assignments_to_avoid.copy()
        new_candidate.assigned_variables = candidate.assigned_variables.copy()

        new_candidate.add_assignments(candidate.assignments)
        if not new_candidate.add_assignment(assignment):
            return None
        new_candidate.add_temporal_relaxations(candidate.temporal_relaxations)
        new_candidate.add_semantic_relaxations(candidate.semantic_relaxations)

        # with this new assignment, find all available/unassigned variables
        for variable in self.tpnu.decision_variables.values():
            # it must not have been assigned
            if not variable in new_candidate.assigned_variables:
                # and the guard must have been satisfied
                if len(variable.guards) == 0 or variable.guards <= new_candidate.assignments:
                    new_candidate.unassigned_variables.put(variable)
                    new_candidate.h += variable.optimal_utility

        return new_candidate

    def create_child_candidate_from_relaxations(self,candidate,relaxations=None,allocations=None):

        new_candidate = Candidate()

        new_candidate.resolved_conflicts = candidate.resolved_conflicts.copy()
        new_candidate.continuously_resolved_cycles = candidate.continuously_resolved_cycles.copy()
        new_candidate.assignments_to_avoid = candidate.assignments_to_avoid.copy()
        new_candidate.assigned_variables = candidate.assigned_variables.copy()

        new_candidate.add_assignments(candidate.assignments)
        # We do not need the following line as it adds duplicated relaxations to the
        # new candidate.
        # new_candidate.add_temporal_relaxations(candidate.temporal_relaxations)
        # Add temporal relaxations
        if relaxations is not None:
            for relaxation in relaxations:
                if not new_candidate.add_temporal_relaxation(relaxation):
                    return None

        # Add temporal allocations
        if allocations is not None:
            for allocation in allocations:
                if not new_candidate.add_temporal_allocation(allocation):
                    return None

        new_candidate.add_semantic_relaxations(candidate.semantic_relaxations)

        # find all available variables
        for variable in self.tpnu.decision_variables.values():
            # it must not have been assigned
            if not variable in new_candidate.assigned_variables:
                # and the guard must have been satisfied
                if len(variable.guards) == 0 or variable.guards <= new_candidate.assignments:
                    new_candidate.unassigned_variables.put(variable)
                    new_candidate.h += variable.optimal_utility

        return new_candidate

    def consistent(self,candidate):
        # Check if this candidate results
        # in a consistent temporal network
        # print('------Consistency check')
        # candidate.pretty_print()

        self.implement(candidate)
        # return either a conflict, or None
        # run the dc checking algorithm
        # TODO: fix the conflict extraction code
        conflict = None

        if self.feasibility_type == FeasibilityType.CONSISTENCY:
            conflict = TemporalConsistency.check(self.tpnu)
        elif self.feasibility_type == FeasibilityType.STRONG_CONTROLLABILITY:
            conflict = StrongControllability.check(self.tpnu)
        elif self.feasibility_type == FeasibilityType.DYNAMIC_CONTROLLABILITY:
            conflict = DynamicControllability.check(self.tpnu)
        else:
            raise Exception("Unknown feasibility type: " + str(self.feasibility_type))

        # the conflict is a collection of dictionaries
        # each represents a negative cycle
        if conflict is None:
            return None
        else:
            # reformat the conflict
            kirk_conflict = Conflict()
            kirk_conflict.add_negative_cycles(conflict,self.tpnu)
            # kirk_conflict.pretty_print()
            # print("Conflict size: " + str(len(kirk_conflict.negative_cycles)))
            return kirk_conflict

    def implement(self,candidate):
        # update the list of active temporal
        # constraints and their bounds
        # for consistency checking

        for constraint in self.tpnu.temporal_constraints.values():
            if set(constraint.guards) <= set(candidate.assignments):
                # print("Activating: ",constraint.id)
                constraint.activated = True
            else:
                # print("Deactivating: ",constraint.id)
                constraint.activated = False

            constraint.relaxed_lb = None
            constraint.relaxed_ub = None

        for relaxation in candidate.temporal_relaxations:
            relaxation.implement()

        for allocation in candidate.temporal_allocations:
            allocation.implement()

    def add_candidate_to_queue(self, candidate):
        self.queue.put(candidate)
        # print("Adding new candidate to queue: " + str(self.queue.qsize()))
        # candidate.pretty_print()

    def pretty_print(self):
        print("Search Problem")

        print("Queue Size# "+ str(self.queue.qsize()))
        print("Known Conflict# "+ str(len(self.known_conflicts)))
