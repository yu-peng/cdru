__author__ = 'yupeng'

from pulp import solvers, LpProblem, LpVariable, value, LpMaximize
from search.temporal_relaxation import TemporalRelaxation

class MaxFlexRelaxation():

    @staticmethod
    def generate_maxflex_relaxations(candidate,negative_cycle):

        if len(negative_cycle.constraints) == 0:
            return None,0

        all_cycles = candidate.continuously_resolved_cycles.copy()
        all_cycles.add(negative_cycle)

        # Solve using PuLP, TODO, incorporate interface to other solvers,
        # especially for nonlinear objective functions
        prob = LpProblem("MaxFlexConflictResolution", LpMaximize)

        # Solve using PyOpt/Snopt,
        # especially for nonlinear constraints/objective functions

        # construct variables and constraints
        lp_variables = {}
        lp_objective = []

        max_flex_variable = LpVariable("Max Flex",0, None)
        lp_objective.append(max_flex_variable)

        # status indicating the feasibility of the relaxation problem
        # 1 is feasible
        # 0 is infeasible
        # Note that this variable is shared by PuLP for its result
        status = 1;

        # We only consider the relaxation of the upper bound of
        # uncontrollable duration.
        # which means that we basically ignore the definition of
        # 'relaxable bounds' in the network, and only consider the upper bounds
        # of uncertain durations.

        for cycle in all_cycles:

            lp_constraint = []

            for constraint, bound in cycle.constraints.keys():
                # The constraint is a pair (temporal_constraint,0/1)
                # where 0 or 1 represent if it is the lower or upper bound

                # first we define the variables
                # which only come from relaxable bounds of constraints
                # in other words, if no constraint in a negative cycle is
                # relaxable, the LP is infeasible
                # and we can stop here

                # TODO: add handler for uncontrollable duration
                variable = None
                if (constraint, bound) in lp_variables:
                    variable = lp_variables[(constraint, bound)]

                coefficient = cycle.constraints[(constraint, bound)]

                if variable is None:
                    if bound == 0:
                        variable = constraint.lower_bound

                    elif bound == 1:
                        # upper bound, the domain is larger than the original UB
                        # if the constraint is not relaxable, fix its domain
                        if not constraint.controllable:
                            variable = LpVariable(constraint.id + "-UB",constraint.lower_bound, constraint.upper_bound)
                            lp_variables[(constraint,bound)] = variable
                            # add the variable to the objective function

                            max_flex_constraint = []
                            max_flex_constraint.append((variable-constraint.lower_bound))
                            max_flex_constraint.append(-1.0*max_flex_variable)
                            prob += sum(max_flex_constraint) >= 0
                        else:
                            variable = constraint.upper_bound

                    assert variable is not None

                lp_constraint.append(variable*coefficient)

            # add the constraint to the problem
            # print(str(lp_constraint))
            if sum(lp_constraint) >= 0:
                # print(str(sum(lp_constraint)) + " >= 0")
                prob += sum(lp_constraint) >= 0
            else:
                status = 0;
                # this is not resolvable
                # no need to proceed

        if status > 0:
            # Set the objective function
            prob += sum(lp_objective)
            # for c in prob.constraints:
            #     print("CON: ", prob.constraints[c])
            # print("OBJ: ", prob.objective)

            # Solve the problem
            try:
                import gurobipy
                status = prob.solve(solvers.GUROBI(mip=False,msg=False))
            except ImportError:
                pass # Gurobi doesn't exist, use default Pulp solver.
                status = prob.solve()

            # exit(0);


        # if no solution was found, do nothing

        if status > 0:
            # A solution has been bound
            # extract the result and store them into a set of relaxation
            # the outcome is a set of relaxations
            relaxations = []
            max_flex_value = value(max_flex_variable)

            for constraint, bound in lp_variables.keys():
                variable = lp_variables[(constraint, bound)]
                relaxed_bound = value(variable)

                if bound == 0:
                    # check if this constraint bound is relaxed
                    if relaxed_bound != constraint.lower_bound:
                        # yes! create a new relaxation for it
                        relaxation = TemporalRelaxation(constraint)
                        relaxation.relaxed_lb = relaxed_bound
                        # relaxation.pretty_print()
                        relaxations.append(relaxation)

                elif bound == 1:
                    # same for upper bound
                    if relaxed_bound != constraint.upper_bound:
                        # yes! create a new relaxation for it
                        relaxation = TemporalRelaxation(constraint)
                        relaxation.relaxed_ub = relaxed_bound
                        # relaxation.pretty_print()
                        relaxations.append(relaxation)

            if len(relaxations) > 0:
                return relaxations,max_flex_value

        return None,0

