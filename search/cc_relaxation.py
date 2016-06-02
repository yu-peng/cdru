__author__ = 'yupeng'

from search.candidate import Candidate
from search.conflict import NegativeCycle
from temporal_network.tpnu import FeasibilityType
from temporal_network.temporal_constraint import TemporalConstraint
from search.temporal_relaxation import TemporalRelaxation
import pysnopt.snopt as snopt
import numpy as np

class ChanceConstrainedRelaxation():

    @staticmethod
    def generate_cc_relaxations(candidate,negative_cycle,feasibility_type,pInfinity=1e6,nInfinity=-1e6):

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
                            # print("LB cost " + str(constraint.relax_cost_lb) + "/" + constraint.name)

                            variable = numVar
                            variables[(constraint, bound)] = variable
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
                        if constraint.relaxable_ub:
                            # print("UB cost " + str(constraint.relax_cost_ub) + "/" + constraint.name)

                            variable = numVar
                            variables[(constraint, bound)] = variable
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
            cc_constraint['lb'] = 0
            cc_constraint['ub'] = 0.05
            constraints.append(cc_constraint)

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
                variable_bounds[lb_var] = [nInfinity, pInfinity]
                variable_bounds[ub_var] = [nInfinity, pInfinity]

                list_iG.append(len(constraints))
                list_jG.append(lb_var + 1)
                neG_count += 1
                list_iG.append(len(constraints))
                list_jG.append(ub_var + 1)
                neG_count += 1

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

        # print("Input parameters for snoptA")
        # print(str(Cold))
        # print(str(neF))
        # print(str(n))
        # print(str(nxname))
        # print(str(nFname))
        #
        # print("Objs")
        # print(str(ObjAdd))
        # print(str(ObjRow))
        # print(str(Prob))
        # print(str(usrf))
        #
        # print("A matrix")
        # print(str(iAfun))
        # print(str(jAvar))
        # print(str(A))
        #
        # print(str(lenA))
        # print(str(neA))
        #
        # print("G matrix")
        # print(str(iGfun))
        # print(str(jGvar))
        #
        # print(str(lenG))
        # print(str(neG))
        #
        # print("Bounds")
        # print(str(xlow))
        # print(str(xupp))
        # print(str(xnames))
        #
        # print(str(Flow))
        # print(str(Fupp))
        # print(str(Fnames))
        #
        # print("States")
        # print(str(x))
        # print(str(xstate))
        # print(str(xmul))
        #
        # print(str(F))
        # print(str(Fstate))
        # print(str(Fmul))
        #
        # print("INFO")
        # print(str(INFO))
        # print(str(mincw))
        # print(str(miniw))
        # print(str(minrw))
        #
        # print("Last row")
        # print(str(nS))
        # print(str(nInf))
        # print(str(sInf))
        # print(str(cw))
        # print(str(iw))
        # print(str(rw))


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

        if status > 0:

            # A solution has been found
            # extract the result and store them into a set of relaxation
            # the outcome is a set of relaxations
            relaxations = []

            # print("Found relaxation")
            for constraint, bound in variables.keys():
                variable = variables[(constraint, bound)]
                relaxed_bound = x[variable]
                # print(str(variable) + "==" + str(x[variable]))

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

            # print("")

            if len(relaxations) > 0:
                return relaxations, 0

        return None, 0

def usrf(status, x, needF, neF, F, needG, neG, G, cu, iu, ru):

    """
    ==================================================================
    Computes the nonlinear objective and constraint terms for the
    problem.
    ==================================================================
    """

    return 0


if __name__ == "__main__":

    candidate = Candidate()
    ev1 = 1
    ev2 = 2
    ev3 = 3

    ep1 = TemporalConstraint('ep-1','ep-1', ev1, ev2, 15,30)
    ep2 = TemporalConstraint('ep-2','ep-2', ev2, ev3, 15,20)
    ep3 = TemporalConstraint('ep-3','ep-3', ev1, ev3, 15,100)
    ep1.controllable = False
    ep1.relaxable_lb = True
    ep1.relaxable_ub = True
    ep2.relaxable_lb = True
    ep2.relaxable_ub = True
    ep1.relax_cost_lb = 10
    ep1.relax_cost_ub = 10
    ep2.relax_cost_lb = 1
    ep2.relax_cost_ub = 1


    new_cycle = NegativeCycle()
    new_cycle.add_constraint(ep1,0,1)
    new_cycle.add_constraint(ep1,1,-1)
    new_cycle.add_constraint(ep2,0,-1)
    new_cycle.add_constraint(ep2,1,1)

    ChanceConstrainedRelaxation.generate_cc_relaxations(candidate,new_cycle,FeasibilityType.STRONG_CONTROLLABILITY)