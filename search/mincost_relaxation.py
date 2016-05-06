__author__ = 'yupeng'

from pulp import solvers, LpProblem, LpMinimize, LpVariable, value
from search.temporal_relaxation import TemporalRelaxation

class MinCostRelaxation():

    @staticmethod
    def generate_mincost_relaxations(candidate,negative_cycle):

        all_cycles = candidate.continuously_resolved_cycles.copy()
        all_cycles.add(negative_cycle)

        # Solve using PuLP, TODO, incorporate interface to other solvers,
        # especially for nonlinear objective functions
        prob = LpProblem("MinCostConflictResolution", LpMinimize)

        # Solve using PyOpt/Snopt,
        # especially for nonlinear constraints/objective functions

        # construct variables and constraints
        lp_variables = {}
        lp_objective = []

        # status indicating the feasibility of the relaxation problem
        # 1 is feasible
        # 0 is infeasible
        # Note that this variable is shared by PuLP for its result
        status = 1;
        # print("Cycles: " + str(len(all_cycles)))
        for cycle in all_cycles:

            lp_ncycle_constraint = []

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
                        # lower bound, the domain is less than the original LB
                        # if the constraint is not relaxable, fix its domain
                        if constraint.relaxable_lb:
                            # print("LB cost " + str(constraint.relax_cost_lb) + "/" + constraint.name)

                            if constraint.controllable:
                                variable = LpVariable(constraint.id + "-LB",None,constraint.lower_bound)
                                # print("New LB VAR: " + str(variable) + " [" + str(None) + "," + str(constraint.lower_bound) + "]")
                                # add the variable to the objective function
                                lp_variables[(constraint,bound)] = variable
                                lp_objective.append((constraint.lower_bound - variable) * constraint.relax_cost_lb)
                            else:
                                variable = LpVariable(constraint.id + "-LB",constraint.lower_bound, constraint.upper_bound)
                                # print("New LB-UC VAR: " + str(variable) + " [" + str(None) + "," + str(constraint.lower_bound) + "]")
                                # add the variable to the objective function
                                lp_variables[(constraint,bound)] = variable
                                lp_objective.append((variable - constraint.lower_bound) * constraint.relax_cost_lb)

                                # Add an additional constraint to make sure that
                                # the lower bound is smaller than the upper bound
                                if (constraint,1) in lp_variables:
                                    ub_variable = lp_variables[(constraint,1)]
                                    uncertain_duration_constraint = []
                                    uncertain_duration_constraint.append((ub_variable - variable))
                                    prob += sum(uncertain_duration_constraint) >= 0
                        else:
                            variable = constraint.lower_bound

                    elif bound == 1:
                        # upper bound, the domain is larger than the original UB
                        # if the constraint is not relaxable, fix its domain
                        if constraint.relaxable_ub:
                            # print("UB cost " + str(constraint.relax_cost_ub) + "/" + constraint.name)

                            if constraint.controllable:
                                variable = LpVariable(constraint.id + "-UB",constraint.upper_bound, None)
                                # print("New UB VAR: " + str(variable) + " [" + str(constraint.upper_bound) + "," + str(None) + "]")
                                # add the variable to the objective function
                                lp_variables[(constraint,bound)] = variable
                                lp_objective.append((variable - constraint.upper_bound) * constraint.relax_cost_ub)
                            else:
                                variable = LpVariable(constraint.id + "-UB",constraint.lower_bound, constraint.upper_bound)
                                # print("New UB-UC VAR: " + str(variable) + " [" + str(constraint.upper_bound) + "," + str(None) + "]")
                                lp_variables[(constraint,bound)] = variable
                                lp_objective.append((constraint.upper_bound - variable) * constraint.relax_cost_ub)

                                # Add an additional constraint to make sure that
                                # the lower bound is smaller than the upper bound
                                if (constraint,0) in lp_variables:
                                    lb_variable = lp_variables[(constraint,0)]
                                    uncertain_duration_constraint = []
                                    uncertain_duration_constraint.append((variable - lb_variable))
                                    prob += sum(uncertain_duration_constraint) >= 0
                        else:
                            variable = constraint.upper_bound


                    assert variable is not None
                # print("Adding variable " + str(coefficient) + "*"+str(variable))
                lp_ncycle_constraint.append(variable*coefficient)

            # add the constraint to the problem
            # print(str(lp_ncycle_constraint))
            if sum(lp_ncycle_constraint) >= 0:
                # print(str(sum(lp_ncycle_constraint)) + " >= 0")
                # Over relax a bit to account for precision issues
                prob += sum(lp_ncycle_constraint) >= 0.0
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
                # pass # Gurobi doesn't exist, use default Pulp solver.
                status = prob.solve()

            # exit(0);

        # print("Computing relaxation")
        # if no solution was found, do nothing

        if status > 0:

            # A solution has been found
            # extract the result and store them into a set of relaxation
            # the outcome is a set of relaxations
            relaxations = []

            # print("Found relaxation")
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
                return relaxations,0

        return None,0