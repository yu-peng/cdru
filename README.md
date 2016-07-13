# Conflict-Directed Relaxation under Uncertainty (CDRU)

This is a python implementation of the Conflict-directed Relaxation with Uncertainty algorithm for solving over-constrained temporal problems. It supports the resolution of many commonly used temporal formulations, including STN, STNU, ccp-STP and their conditional variants. All these formulations can be loaded into a TPNU object.

## Quickstart

There are many examples you may refer to in tests.py inside the search folder. Here is a simple example of using CDRU to solve an over-constrained TPNU.

1. Load the problem: depending on the file format used (CCTP os TPN), you may choose from the following two ways to load a TPNU object from file.

    * For *.cctp files, you may load using function `tpnu = Tpnu.parseCCTP(path)`.

    * For *.tpn files, you need to use an additional conversion function: `obj = Tpn.parseTPN(path)` and `tpnu = Tpnu.from_tpn_autogen(obj)`.

2. Construct the search problem: `search_problem = SearchProblem(tpnu,f_type,o_type,c_type)`. The constructor needs the tpnu object and three parameters:

    * `f_type`: the feasibility model used by CDRU. The three options are: `FeasibilityType.CONSISTENCY`, `FeasibilityType.STRONG_CONTROLLABILITY`, and `FeasibilityType.STRONG_CONTROLLABILITY`. 

    * `o_type`: the objective function used by CDRU. The two options are: `ObjectiveType.MIN_COST` and `ObjectiveType.MAX_FLEX_UNCERTAINTY`. Currently, the second option is only used for some RCPSP problems, which are feasible and require CDRU to find the maximum range that can be built into the uncertain durations while maintaining Strong/Dynamic controllability. The default LP solver is PuLP. Gurobi is also supported if you have it installed. 
 
    * `c_type`: the switch for chance constraint. The two options are: `ChanceConstrained.OFF` and `ChanceConstrained.ON`. Chance constrained relaxation requires the installation of SNOPT (version 7.2) and its python interface, pysnopt (https://github.com/b45ch1/pysnopt).
 
3. Search for solutions: `solution = search_problem.next_solution()`. The return solution is a `Candidate` object that contains assignments to discrete variables and temporal relaxations (if applicable). You can use `solution.pretty_print()` to print the candidate object. If no solution (or no more solution) can befound, the `next_solution()` function will return `None`. 


## Examples

There are quite a few test problems in the `examples` folder. They come in a few different types:

1. `AUV-*.cctp` files are CCTP problems generated from autonomous underwater vehicle mission scenarios. You may solve it with all three feasibility types, the minimal cost objective, and both chance constraint ON and OFF.

2. `PSP1.SCH*.cctp` files are generated from partial ordered activities for Resource-Constrained Project Scheduling Problems. You may solve it with the dynamic controllability model, the maximum flexibility objective, and chance constraint OFF.
 
3. `Route_Red_Headway_*` files are generated from Boston's Red Line subway schedule. You may solve it with the dynamic controllability model, the minimal cost objective, and chance constraint OFF.


## References

The implementation is based on the following papers:

1. Conflict-directed continuous relaxation framework.

    Peng Yu and Brian Williams, Continuously relaxing over-constrained conditional temporal problems through generalized conflict learning and resolution. In Proceedings of the 23th International Joint Conference on Artificial Intelligence (IJCAI-2013), pp. 2429–2436.

2. Conflict learning from controllability checking algorithms.

    Peng Yu and Cheng Fang and Brian Williams, Resolving uncontrollable conditional temporal problems using continuous relaxations. In Proceedings of the Twenty-fourth International Conference on Automated Planning and Scheduling (ICAPS-2014), pp. 341–349.

3. Chance-constrained probabilistic scheduling.

    Fang Cheng, Peng Yu and Brian Williams, Chance-constrained probabilistic simple temporal problems. In Proceedings of the Twenty-Eighth AAAI Conference on Artificial Intelligence (AAAI-14), pp. 2264–2270.

4. Chance-constrained relaxations for probabilistic temporal problems.

    Peng Yu and Cheng Fang and Brian Williams, Resolving over-constrained probabilistic temporal problems. In Proceedings of the Twenty-Eighth AAAI Conference on Artificial Intelligence (AAAI-15).

5. Robustness analysis of temporal problems.

    Jing Cui and Peng Yu and Cheng Fang and Patrik Haslum and Brian Williams, Optimising bounds in simple temporal networks with uncertainty under dynamic controllability constraints. In Proceedings of the Twenty-fifth International Conference on Automated Planning and Scheduling (ICAPS-2015), pp. 52–60.