import scipy

from search.chance_constraint_relaxation import ChanceConstraintRelaxation
from search.temporal_allocation import TemporalAllocation
from temporal_network.chance_constraint import ChanceConstraint

__author__ = 'yupeng'

from search.candidate import Candidate
from search.conflict import NegativeCycle
from temporal_network.tpnu import FeasibilityType
from temporal_network.temporal_constraint import TemporalConstraint
from search.temporal_relaxation import TemporalRelaxation
import pysnopt.snopt as snopt
import numpy as np
from scipy.stats import norm, truncnorm

prob_means = []
prob_stds = []

class ChanceConstrainedRelaxation():

    @staticmethod
    def generate_cc_relaxations(candidate,negative_cycle,feasibility_type,cc,pInfinity=1e6,nInfinity=-1e6):

        global prob_means
        global prob_stds
        global prob_vars
        global cc_var

        all_cycles = candidate.continuously_resolved_cycles.copy()
        all_cycles.add(negative_cycle)
        # print("CC Solving against " + str(len(all_cycles)) + " cycles")

        numVar = 0
        numConstraint = 0

        # Solve using Snopt,
        # especiallFy for nonlinear constraints/objective functions

        # construct variables and constraints
        variables = {}
        variable_bounds = {}
        initial_values = {}
        constraints = []
        objective = {}

        list_iA = []
        list_jA = []
        list_A = []
        neA_count = 0

        list_iG = []
        list_jG = []
        neG_count = 0

        prob_durations = set()
        prob_means = []
        prob_stds = []
        prob_vars = []
        cc_var = -1

        # status indicating the feasibility of the relaxation problem
        # 1 is feasible
        # 0 is infeasible
        # Note that this variable is shared by PuLP for its result
        status = 1;

        # print("Cycles: " + str(len(all_cycles)))
        for cycle in all_cycles:
            lp_ncycle_constraint = {}
            rhs = 0

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
                if (constraint, bound) in variables:
                    variable = variables[(constraint, bound)]

                coefficient = cycle.constraints[(constraint, bound)]

                if variable is None:
                    if bound == 0:
                        # lower bound, the domain is less than the original LB
                        # if the constraint is not relaxable, fix its domain
                        if constraint.relaxable_lb or (not constraint.controllable and constraint.probabilistic):
                        # if constraint.relaxable_lb:
                            # print("LB cost " + str(constraint.relax_cost_lb) + "/" + constraint.name)

                            variable = numVar
                            variables[(constraint, bound)] = variable
                            initial_values[variable] = constraint.get_lower_bound()
                            numVar += 1

                            if constraint.controllable or feasibility_type == FeasibilityType.CONSISTENCY:
                                # add the variable to the objective function

                                variable_bounds[variable] = [nInfinity,constraint.lower_bound]
                                objective[variable] = [-1*constraint.relax_cost_lb,constraint.lower_bound*constraint.relax_cost_lb]

                            else:
                                variable_bounds[variable] = [constraint.lower_bound,constraint.upper_bound-0.001]

                                # We collect all probabilistic durations
                                # for encoding the chance constraint
                                if constraint.probabilistic:
                                    prob_durations.add(constraint)
                                else:
                                    objective[variable] = [constraint.relax_cost_lb,
                                                           -1 * constraint.lower_bound * constraint.relax_cost_lb]

                                    # Add an additional constraint to make sure that
                                    # the lower bound is smaller than the upper bound
                                    # Only for non-probabilistic constraint
                                    if (constraint, 1) in variables :
                                        ub_variable = variables[(constraint, 1)]

                                        constraint = {}
                                        constraint[ub_variable] = 1
                                        constraint[variable] = -1
                                        constraint['lb'] = 0.001
                                        constraint['ub'] = pInfinity

                                        constraints.append(constraint)

                                        list_iA.append(len(constraints))
                                        list_jA.append(ub_variable + 1)
                                        list_A.append(1)
                                        neA_count += 1

                                        list_iA.append(len(constraints))
                                        list_jA.append(variable + 1)
                                        list_A.append(-1)
                                        neA_count += 1

                            lp_ncycle_constraint[variable] = coefficient

                        else:
                            variable = constraint.lower_bound
                            rhs -= constraint.lower_bound*coefficient

                    elif bound == 1:
                        # upper bound, the domain is larger than the original UB
                        # if the constraint is not relaxable, fix its domain
                        if constraint.relaxable_ub or (not constraint.controllable and constraint.probabilistic):
                        # if constraint.relaxable_ub:
                            # print("UB cost " + str(constraint.relax_cost_ub) + "/" + constraint.name)

                            variable = numVar
                            variables[(constraint, bound)] = variable
                            initial_values[variable] = constraint.get_upper_bound()
                            numVar += 1

                            if constraint.controllable or feasibility_type == FeasibilityType.CONSISTENCY:
                                variable_bounds[variable] = [constraint.upper_bound, pInfinity]
                                objective[variable] = [constraint.relax_cost_ub,-1*constraint.upper_bound*constraint.relax_cost_ub]

                            else:
                                variable_bounds[variable] = [constraint.lower_bound+0.001, constraint.upper_bound]

                                # We collection all probabilistic durations
                                # for encoding the chance constraint
                                if constraint.probabilistic:
                                    prob_durations.add(constraint)
                                else:
                                    objective[variable] = [-1 * constraint.relax_cost_ub,
                                                           constraint.upper_bound * constraint.relax_cost_ub]

                                    # Add an additional constraint to make sure that
                                    # the lower bound is smaller than the upper bound
                                    # Only for non-probabilistic constraint
                                    if (constraint, 0) in variables:
                                        lb_variable = variables[(constraint, 0)]

                                        constraint = {}
                                        constraint[variable] = 1
                                        constraint[lb_variable] = -1
                                        constraint['lb'] = 0.001
                                        constraint['ub'] = pInfinity

                                        constraints.append(constraint)

                                        list_iA.append(len(constraints))
                                        list_jA.append(variable + 1)
                                        list_A.append(1)
                                        neA_count += 1

                                        list_iA.append(len(constraints))
                                        list_jA.append(lb_variable + 1)
                                        list_A.append(-1)
                                        neA_count += 1

                            lp_ncycle_constraint[variable] = coefficient
                        else:
                            variable = constraint.upper_bound
                            rhs -= constraint.upper_bound * coefficient
                    assert variable is not None

                else:
                    lp_ncycle_constraint[variable] = coefficient

                # print("Adding variable " + str(coefficient) + "*"+str(variable))

            # add the ncycle constraint to the problem
            # print(str(lp_ncycle_constraint))
            constraints.append(lp_ncycle_constraint)
            # print("C" + str(len(constraints)) + ": ", end="")
            empty_constraint = True
            for key in lp_ncycle_constraint:
                if lp_ncycle_constraint[key] != 0:
                    list_iA.append(len(constraints))
                    list_jA.append(key + 1)
                    list_A.append(lp_ncycle_constraint[key])
                    neA_count += 1
                    empty_constraint = False

                # constraint,bound = variables[key]
                # print(str(lp_ncycle_constraint[key]) + "*" + "(" +str(key)+ ") ", end="")

            lp_ncycle_constraint['lb'] = rhs+0.0001
            lp_ncycle_constraint['ub'] = pInfinity

            if empty_constraint and rhs > 0:
                # This constraint cannot be met
                return None,0

            # print(">= " + str(rhs))


        # Create the chance constraint
        if len(prob_durations) > 0:
            cc_constraint = {}
            constraints.append(cc_constraint)

            # Check if the chance constraint is relaxable
            if cc.relaxable_bound:
                cc_constraint['lb'] = -1
                cc_constraint['ub'] = 0

                # we need to encode an additional variable
                # to represent cc
                cc_var = numVar
                variables[("CC", 1)] = cc_var
                numVar += 1
                variable_bounds[cc_var] = [cc.risk_bound, pInfinity]

                list_iA.append(len(constraints))
                list_jA.append(cc_var + 1)
                list_A.append(-1)
                neA_count += 1

                # And add cc to the objective function
                objective[cc_var] = [cc.relax_cost, -1 * cc.risk_bound * cc.relax_cost]

            else:
                cc_constraint['lb'] = 0
                cc_constraint['ub'] = cc.risk_bound

            # print("C" + str(len(constraints)) + " (CC): ", end="")
            # print(str(cc_constraint['lb']) + "<= ", end="")

            for constraint in prob_durations:

                if (constraint, 0) in variables:
                    lb_var = variables[(constraint, 0)]
                else:
                    lb_var = numVar
                    variables[(constraint, 0)] = lb_var
                    numVar += 1

                if (constraint, 1) in variables:
                    ub_var = variables[(constraint, 1)]
                else:
                    ub_var = numVar
                    variables[(constraint, 1)] = ub_var
                    numVar += 1

                # override their domain since we are free to
                # allocate any values for them
                variable_bounds[lb_var] = [0, constraint.mean]
                variable_bounds[ub_var] = [constraint.mean, pInfinity]

                # initial_values[lb_var] = constraint.mean - 4*constraint.std
                # initial_values[ub_var] = constraint.mean + 4*constraint.std

                initial_values[lb_var] = constraint.get_lower_bound()
                initial_values[ub_var] = constraint.get_upper_bound()

                list_iG.append(len(constraints))
                list_jG.append(lb_var + 1)
                neG_count += 1
                list_iG.append(len(constraints))
                list_jG.append(ub_var + 1)
                neG_count += 1
                prob_vars.append(lb_var)
                prob_vars.append(ub_var)

                # print("Risk((" + str(lb_var) + ")--"+str(constraint.mean)+"--"+str(constraint.std)+"--("+str(ub_var)+")) ", end="")

                prob_means.append(constraint.mean)
                prob_stds.append(constraint.std)

            # print("<= " + str(cc_constraint['ub']))

        # Add the objective as the last constraint
        constraints.append(objective)

        for key in objective:
            list_iA.append(len(constraints))
            list_jA.append(key + 1)
            list_A.append(objective[key][0])

            if objective[key][0] != 0:
                neA_count += 1

        objective['lb'] = nInfinity
        objective['ub'] = pInfinity


        # Start Constructing the problem!!
        # Solve using SNOPT
        snopt.check_memory_compatibility()

        # minrw, miniw, mincw defines how much character, integer and real
        # storeage is neede to solve the problem.
        # ! assigned by SNOPT
        minrw = np.zeros((1), dtype=np.int32)
        miniw = np.zeros((1), dtype=np.int32)
        mincw = np.zeros((1), dtype=np.int32)

        # Workspace for character, integer and real arrays.
        # The plus 1 is for the objective function
        rw = np.zeros((2000*(len(variables)+len(constraints)),), dtype=np.float64)
        iw = np.zeros((1000*(len(variables)+len(constraints)),), dtype=np.int32)
        cw = np.zeros((8 * 500,), dtype=np.character)

        # rw = np.zeros((10000,), dtype=np.float64)
        # iw = np.zeros((10000,), dtype=np.int32)
        # cw = np.zeros((8 * 500,), dtype=np.character)

        # The Start variable for SnoptA
        Cold = np.array([0], dtype=np.int32)
        Basis = np.array([1], dtype=np.int32)
        Warm = np.array([2], dtype=np.int32)

        # Variable definitions

        # Initial values
        x = np.zeros((len(variables),), dtype=np.float64)

        # Lower and upper bounds
        xlow = np.zeros((len(variables),), dtype=np.float64)
        xupp = np.zeros((len(variables),), dtype=np.float64)

        for key in variable_bounds:
            if key in initial_values:
                x[key] = initial_values[key]
            bounds = variable_bounds[key]
            xlow[key] = bounds[0]
            xupp[key] = bounds[1]

        # Initial values for x
        xstate = np.zeros((len(variables),), dtype=np.int32)

        # Vector of dual variables for the bound constraints
        # ! assigned by SNOPT
        xmul = np.zeros((len(variables),), dtype=np.float64)


        # Initialize values for constraints
        F = np.zeros((len(constraints),), dtype=np.float64)

        # Lower and upper bounds for constraints
        Flow = np.zeros((len(constraints),), dtype=np.float64)
        Fupp = np.zeros((len(constraints),), dtype=np.float64)

        for idx in range(0,len(constraints)):
            constraint = constraints[idx]
            Flow[idx] = constraint['lb']
            Fupp[idx] = constraint['ub']


        # Initial states
        Fstate = np.zeros((len(constraints),), dtype=np.int32)
        # Estimate of the vector of Lagrange multipliers.
        # Since we know nothing about it at the moment. Set it to zero.
        Fmul = np.zeros((len(constraints),), dtype=np.float64)

        # Constant added to the objective row for
        # printing purposes
        ObjAdd = np.zeros((1,), dtype=np.float64)
        ObjAdd[0] = 0

        # The last row F is the objective function
        ObjRow = np.zeros((1,), dtype=np.int32)
        ObjRow[0] = len(constraints) # NOTE: We must add one to mesh with fortran */

        # Reports the result of the call to snOptA
        INFO = np.zeros((1,), dtype=np.int32)

        # Set number of variables
        n = np.zeros((1,), dtype=np.int32)
        n[0] = len(variables)

        # Set the number of functions (constraints and objectives)
        # in F
        neF = np.zeros((1,), dtype=np.int32)
        neF[0] = len(constraints)

        # dimension of arrays iAfun, jAvar and A
        # They contain the nonzero elements of the linear part A

        lenA = np.zeros((1,), dtype=np.int32)
        lenA[0] = len(list_iA)
        neA = np.zeros((1,), dtype=np.int32)
        neA[0] = neA_count

        # iAfun = np.zeros((lenA[0],), dtype=np.int32)
        # jAvar = np.zeros((lenA[0],), dtype=np.int32)
        # A = np.zeros((lenA[0],), dtype=np.float64)

        if lenA[0] > 0:
            iAfun = np.array(list_iA, dtype=np.int32)
            jAvar = np.array(list_jA, dtype=np.int32)
            A = np.array(list_A, dtype=np.float64)
        else:
            lenA[0] = 1
            iAfun = np.zeros((lenA[0],), dtype=np.int32)
            jAvar = np.zeros((lenA[0],), dtype=np.int32)
            A = np.zeros((lenA[0],), dtype=np.float64)

        # dimension of arrays iGfun and jGvar
        # They contain the nonzero elements of the nonlinear part of the derivativeG
        lenG = np.zeros((1,), dtype=np.int32)
        lenG[0] = len(list_iG)
        neG = np.zeros((1,), dtype=np.int32)
        neG[0] = neG_count

        if lenG[0] > 0:
            iGfun = np.array(list_iG, dtype=np.int32)
            jGvar = np.array(list_jG, dtype=np.int32)
        else:
            lenG[0] = 1
            iGfun = np.zeros((lenG[0],), dtype=np.int32)
            jGvar = np.zeros((lenG[0],), dtype=np.int32)

        # Generate the usrf function for SNOPT


        # names for variables and constraints
        # By default no names provided (both set to 1)
        nxname = np.zeros((1,), dtype=np.int32)
        nFname = np.zeros((1,), dtype=np.int32)
        nxname[0] = 1
        nFname[0] = 1

        # Names for variables and problem functions
        # not used when nxname and nFname are set to 1
        xnames = np.zeros((1 * 8,), dtype=np.character)
        Fnames = np.zeros((1 * 8,), dtype=np.character)
        Prob = np.zeros((200 * 8,), dtype=np.character)


        # final number of superbasic variables
        # ! assigned by SNOPT
        nS = np.zeros((1,), dtype=np.int32)

        # Number and sum of the infeasibilities of constraints
        nInf = np.zeros((1,), dtype=np.int32)
        sInf = np.zeros((1,), dtype=np.float64)




        # Define Print and Summary files
        # Must be called before any other SNOPT routing

        # Unit number for summary file
        iSumm = np.zeros((1,), dtype=np.int32)
        iSumm[0] = 0

        # Unit number for the print file
        iPrint = np.zeros((1,), dtype=np.int32)
        iPrint[0] = 0

        # Unit number for the specs file
        iSpecs = np.zeros((1,), dtype=np.int32)
        iSpecs[0] = 4

        # name for output print and spec files
        printname = np.zeros((200 * 8,), dtype=np.character)
        specname = np.zeros((200 * 8,), dtype=np.character)

        # open output files using snfilewrappers.[ch] */
        specn = "sntoya.spc"
        printn = "sntoya.out"
        specname[:len(specn)] = list(specn)
        printname[:len(printn)] = list(printn)

        # Open the print file, fortran style */
        snopt.snopenappend(iPrint, printname, INFO)


        # ================================================================== */
        # First,  sninit_ MUST be called to initialize optional parameters   */
        # to their default values.                                           */
        # ================================================================== */

        snopt.sninit(iPrint, iSumm, cw, iw, rw)


        # Set configurations
        strOpt = np.zeros((200 * 8,), dtype=np.character)
        DerOpt = np.zeros((1,), dtype=np.int32)

        # set derivative options
        strOpt_s = "Derivative option"
        DerOpt[0] = 1
        strOpt[:len(strOpt_s)] = list(strOpt_s)
        snopt.snseti(strOpt, DerOpt, iPrint, iSumm, INFO, cw, iw, rw)

        # set iteration limit
        Major = np.array([250], dtype=np.int32)
        strOpt_s = "Major Iteration limit"
        strOpt[:len(strOpt_s)] = list(strOpt_s)

        snopt.snseti(strOpt, Major, iPrint, iSumm, INFO, cw, iw, rw)

        # SnoptA will compute the Jacobian by finite-differences.   */
        # The user has the option of calling  snJac  to define the  */
        # coordinate arrays (iAfun,jAvar,A) and (iGfun, jGvar).     */


        #     ------------------------------------------------------------------ */
        #     Go for it, using a Cold start.                                     */
        #     ------------------------------------------------------------------ */

        # print("Computing relaxation")

        snopt.snopta(Cold, neF, n, nxname, nFname,
                     ObjAdd, ObjRow, Prob, usrf,
                     iAfun, jAvar, lenA, neA, A,
                     iGfun, jGvar, lenG, neG,
                     xlow, xupp, xnames, Flow, Fupp, Fnames,
                     x, xstate, xmul, F, Fstate, Fmul,
                     INFO, mincw, miniw, minrw,
                     nS, nInf, sInf, cw, iw, rw, cw, iw, rw)

        snopt.snclose(iPrint)
        snopt.snclose(iSpecs)

        # print("Done computing relaxation")

        # print("Solution " + str(x))

        if INFO[0] == 1:

            # An optimal solution has been found
            # extract the result and store them into a set of relaxation
            # the outcome is a set of relaxations
            relaxations = []
            allocations = []
            cc_relaxations = []

            # print("Found relaxation: INFO=" + str(INFO[0]))

            for constraint, bound in variables.keys():
                variable = variables[(constraint, bound)]
                relaxed_bound = x[variable]
                # print(str(variable) + "==" + str(x[variable]))

                if constraint == "CC":
                    # print("Relaxing CC from " + str(cc.risk_bound) + " to " + str(relaxed_bound))

                    if abs(relaxed_bound-cc.risk_bound) > 0.001:

                        cc_relaxation = ChanceConstraintRelaxation(cc)
                        cc_relaxation.relaxed_bound = relaxed_bound
                        cc_relaxations.append(cc_relaxation)
                    continue

                if not constraint.controllable and constraint.probabilistic:

                    # This is allocation
                    # Both lb and ub variables must have been included in the calculation

                    if bound == 0:
                        lb_variable = variables[(constraint, 0)]
                        ub_variable = variables[(constraint, 1)]
                        allocated_lb = x[lb_variable]
                        allocated_ub = x[ub_variable]

                        allocation = TemporalAllocation(constraint)
                        allocation.allocated_lb = allocated_lb
                        allocation.allocated_ub = allocated_ub
                        # allocation.pretty_print()
                        allocations.append(allocation)

                else:
                    # This is relaxation
                    if bound == 0:
                        # check if this constraint bound is relaxed
                        if abs(relaxed_bound - constraint.lower_bound) > 0.001:
                            # yes! create a new relaxation for it
                            relaxation = TemporalRelaxation(constraint)
                            relaxation.relaxed_lb = relaxed_bound
                            # relaxation.pretty_print()
                            relaxations.append(relaxation)

                    elif bound == 1:
                        # same for upper bound
                        if abs(relaxed_bound - constraint.upper_bound) > 0.001:
                            # yes! create a new relaxation for it
                            relaxation = TemporalRelaxation(constraint)
                            relaxation.relaxed_ub = relaxed_bound
                            # relaxation.pretty_print()
                            relaxations.append(relaxation)

            # print("")

            if len(relaxations) > 0 or len(allocations) > 0:
                return relaxations, allocations, cc_relaxations, 0

        return None, None, None, 0

# def usrf(status, x, needF, neF, F, needG, neG, G, cu, iu, ru):
#     """
#     ==================================================================
#     Computes the nonlinear objective and constraint terms for the
#     problem.
#     ==================================================================
#     """
#
#     return 0


def usrf(status, x, needF, neF, F, needG, neG, G, cu, iu, ru):
    """
    ==================================================================
    Computes the nonlinear objective and constraint terms for the
    problem.
    ==================================================================
    """

    # print('called usrfun with ' + str(len(G)) + ' non-linear variables')

    if (needF[0] != 0):
        # the second last row is for chance constraint
        F[neF[0] - 2] = 0

        if cc_var > 0:
            F[neF[0] - 2] += x[cc_var]

        for idx in range(0, int(len(G)/ 2)):
            mean = prob_means[idx]
            sigma = prob_stds[idx]
            lb_var = prob_vars[2 * idx]
            ub_var = prob_vars[2 * idx+1]
            # print("Mean: " + str(mean) + " / Sigma: " + str(sigma))

            a, b = (0 - mean) / sigma, (1e6 - mean) / sigma

            ub_survival = truncnorm.sf(x[ub_var],a,b, loc=mean, scale=sigma)
            lb_mass = truncnorm.cdf(x[lb_var],a,b, loc=mean, scale=sigma)

            F[neF[0] - 2] += ub_survival + lb_mass

            # print('Updating F['+str(neF[0] - 2)+']: ' + str(x[lb_var]) + '-' + str(x[ub_var]) + ': ' + str(lb_mass) + "+" +str(ub_survival) + "="+str(F[neF[0] - 2]))

    if (needG[0] != 0):
        # Compute the partial derivatives of the chance constraint
        # over the lower and upper bounds of the
        # probabilistic durations
        for idx in range(0, int(len(G) / 2)):
            mean = prob_means[idx]
            sigma = prob_stds[idx]
            lb_var = prob_vars[2 * idx]
            ub_var = prob_vars[2 * idx + 1]

            a, b = (0 - mean) / sigma, (1e6 - mean) / sigma

            # For the lower bound, the derivative is the Gaussian pdf
            G[2 * idx] = truncnorm.pdf(x[lb_var], a,b, loc=mean, scale=sigma)

            # For the upper bound, it is the negation of the Gaussian pdf
            G[2 * idx + 1] = -1 * truncnorm.pdf(x[ub_var], a,b, loc=mean, scale=sigma)

            # print('Updating G['+str(2 * idx)+']: ' + str(G[2 * idx]))
            # print('Updating G['+str(2 * idx+1)+']: ' + str(G[2 * idx + 1]))

if __name__ == "__main__":

    candidate = Candidate()
    ev1 = 1
    ev2 = 2
    ev3 = 3

    ep1 = TemporalConstraint('ep-1','ep-1', ev1, ev2, 15,30)
    ep2 = TemporalConstraint('ep-2','ep-2', ev2, ev3, 15,30)
    ep3 = TemporalConstraint('ep-3','ep-3', ev1, ev3, 40,40)
    ep1.controllable = False
    ep1.probabilistic = True
    ep1.mean = 150
    ep1.std = 5

    ep2.controllable = False
    ep2.probabilistic = True
    ep2.mean = 150
    ep2.std = 5

    ep3.relaxable_ub = True
    ep3.relax_cost_ub = 0.1

    new_cycle = NegativeCycle()
    new_cycle.add_constraint(ep1,0,1)
    new_cycle.add_constraint(ep1,1,-1)
    new_cycle.add_constraint(ep2,0,1)
    new_cycle.add_constraint(ep2,1,-1)
    new_cycle.add_constraint(ep3,1,1)

    cc = ChanceConstraint("CC-1","CC-Constraint",0.05)
    cc.relaxable_bound = True
    cc.relax_cost = 100000

    ChanceConstrainedRelaxation.generate_cc_relaxations(candidate,new_cycle,FeasibilityType.STRONG_CONTROLLABILITY,cc)