
__author__ = 'yupeng'

import unittest
from os.path import join, dirname
from math import fabs
from tpn import Tpn
from controllability.dynamic_controllability import DynamicControllability
from temporal_network.tpnu import Tpnu
from search.search_problem import SearchProblem, FeasibilityType, ObjectiveType
from temporal_network.decision_variable import DecisionVariable
from temporal_network.temporal_constraint import TemporalConstraint
from temporal_network.assignment import Assignment
from search.mip_encode import MipEncode
from datetime import datetime

class SearchTests(unittest.TestCase):
    def setUp(self):
        cdru_dir = dirname(__file__)
        self.examples_dir = join(cdru_dir, join('..', 'examples'))

    # used in most of the tests.
    def assert_cdru_result(self, example_file, expected_result):
        path = join(self.examples_dir, example_file)

        if Tpnu.isCCTP(path):
            tpnu = Tpnu.parseCCTP(path)
        elif Tpnu.isTPN(path):
            obj = Tpn.parseTPN(join(self.examples_dir, example_file))
            tpnu = Tpnu.from_tpn_autogen(obj)
        else:
            raise Exception("Input file " + path + " is neither a CCTP nor a TPN")

        startTime = datetime.now()
        search_problem = SearchProblem(tpnu,FeasibilityType.DYNAMIC_CONTROLLABILITY,ObjectiveType.MIN_COST)
        search_problem.initialize()

        solution = search_problem.next_solution()

        runtime = datetime.now() - startTime

        print("----------------------------------------")
        if solution is not None:
            print(example_file)
            solution.pretty_print()
            # print(solution.json_print(example_file,"CDRU+PuLP",runtime.total_seconds()))
        else:
            print(example_file)
            print(None)
            search_problem.pretty_print()
        is_feasible = solution is not None
        self.assertEqual(is_feasible, expected_result)

    # used in most of the tests.
    def assert_mip_result(self, example_file, expected_result):
        path = join(self.examples_dir, example_file)

        if Tpnu.isCCTP(path):
            tpnu = Tpnu.parseCCTP(path)
        elif Tpnu.isTPN(path):
            obj = Tpn.parseTPN(join(self.examples_dir, example_file))
            tpnu = Tpnu.from_tpn_autogen(obj)
        else:
            raise Exception("Input file " + path + " is neither a CCTP nor a TPN")

        startTime = datetime.now()
        mip_solver = MipEncode(tpnu,ObjectiveType.MIN_COST)
        solution = mip_solver.mip_solver()

        runtime = datetime.now() - startTime

        print("----------------------------------------")
        if solution is not None:
            print(example_file)
            solution.pretty_print()
            # print(solution.json_print(example_file,"CDRU+PuLP",runtime.total_seconds()))
        else:
            print(example_file)
            print(None)
            #search_problem.pretty_print()
        is_feasible = solution is not None
        self.assertEqual(is_feasible, expected_result)

    def assert_max_flex_result(self, example_file, expected_result):
        path = join(self.examples_dir, example_file)

        if Tpnu.isCCTP(path):
            tpnu = Tpnu.parseCCTP(path)
        elif Tpnu.isTPN(path):
            obj = Tpn.parseTPN(join(self.examples_dir, example_file))
            tpnu = Tpnu.from_tpn_autogen(obj)
        else:
            raise Exception("Input file " + path + " is neither a CCTP nor a TPN")

        search_problem = SearchProblem(tpnu,FeasibilityType.DYNAMIC_CONTROLLABILITY,ObjectiveType.MAX_FLEX_UNCERTAINTY)
        search_problem.initialize()

        solution = search_problem.next_solution()

        print("----------------------------------------")
        if solution is not None:
            print(example_file)
            solution.pretty_print()
        else:
            print(example_file)
            print(None)
            search_problem.pretty_print()
        is_feasible = solution is not None
        self.assertEqual(is_feasible, expected_result)


    def compare_cdru_mip(self, example_file, expected_result):
        path = join(self.examples_dir, example_file)

        if Tpnu.isCCTP(path):
            tpnu = Tpnu.parseCCTP(path)
        elif Tpnu.isTPN(path):
            obj = Tpn.parseTPN(join(self.examples_dir, example_file))
            tpnu = Tpnu.from_tpn_autogen(obj)
        else:
            raise Exception("Input file " + path + " is neither a CCTP nor a TPN")

        search_problem = SearchProblem(tpnu,FeasibilityType.DYNAMIC_CONTROLLABILITY,ObjectiveType.MAX_FLEX_UNCERTAINTY)
        search_problem.initialize()

        solution = search_problem.next_solution()

        print("----------------------------------------")
        if solution is not None:
            print(example_file)
            solution.pretty_print()
        else:
            print(example_file)
            print(None)
            search_problem.pretty_print()
        is_feasible = solution is not None
        self.assertEqual(is_feasible, expected_result)

        # test mip_encode

        if Tpnu.isCCTP(path):
            tpnu = Tpnu.parseCCTP(path)
        elif Tpnu.isTPN(path):
            obj = Tpn.parseTPN(join(self.examples_dir, example_file))
            tpnu = Tpnu.from_tpn_autogen(obj)
        else:
            raise Exception("Input file " + path + " is neither a CCTP nor a TPN")
        mip_solver = MipEncode(tpnu)
        solution2 = mip_solver.mip_solver()
        diff = 0
        if fabs(solution.utility - solution2.utility) >= 1e-2 and not(solution.utility >= 100 and solution2.utility >= 100):
            diff = round(solution.utility - solution2.utility,4)
        self.ofile = open('output.txt','a')
        self.ofile.write('%s    %s    %s    %s\n'%(path, solution2.utility, solution.utility, diff))
        self.ofile.close()
        print("----------------------------------------")
        if solution2 is not None:
            print(example_file)
            solution2.pretty_print()
        else:
            print(example_file)
            print(None)

    def assert_mip_maxflex_result(self, example_file, expected_result):
        path = join(self.examples_dir, example_file)

        if Tpnu.isCCTP(path):
            tpnu = Tpnu.parseCCTP(path)
        elif Tpnu.isTPN(path):
            obj = Tpn.parseTPN(join(self.examples_dir, example_file))
            tpnu = Tpnu.from_tpn_autogen(obj)
        else:
            raise Exception("Input file " + path + " is neither a CCTP nor a TPN")

        startTime = datetime.now()
        mip_solver = MipEncode(tpnu,ObjectiveType.MAX_FLEX_UNCERTAINTY)
        solution = mip_solver.mip_solver()

        runtime = datetime.now() - startTime

        print("----------------------------------------")
        if solution is not None:
            print(example_file)
            solution.pretty_print()
            # print(solution.json_print(example_file,"CDRU+PuLP",runtime.total_seconds()))
        else:
            print(example_file)
            print(None)
            #search_problem.pretty_print()
        is_feasible = solution is not None
        self.assertEqual(is_feasible, expected_result)
            
#     def test_cdru_basic(self):
#         self.assert_cdru_result('test1.tpn', True)
#         self.assert_cdru_result('test2.tpn', True)
#         self.assert_cdru_result('test3.tpn', True)
#         self.assert_cdru_result('test4.tpn', True)
#  
#     def test_whoi(self):
#         self.assert_cdru_result('whoi-1.cctp', True)
#         self.assert_cdru_result('whoi-2.cctp', True)
#  
#     def test_bus_schedule(self):
#         self.assert_cdru_result('Route1_2_1.cctp', True)
#         self.assert_cdru_result('Route1_2_2.cctp', True)
#  
#     def test_bus_selection(self):
#         self.assert_cdru_result('bus-1.cctp', True)
#         self.assert_cdru_result('bus-2.cctp', True)
#         self.assert_cdru_result('bus-3.cctp', False)
#         self.assert_cdru_result('bus-4.cctp', True)
#  
#     def test_cctp_zipcar(self):
#         self.assert_cdru_result('Zipcar-1.cctp', True)
#         self.assert_cdru_result('Zipcar-2.cctp', True)
#         self.assert_cdru_result('Zipcar-3.cctp', True)
#         self.assert_cdru_result('Zipcar-4.cctp', True)
#  
#     def test_tpn_zipcar(self):
#         self.assert_cdru_result('Zipcar-1.tpn', True)
#         self.assert_cdru_result('Zipcar-2.tpn', True)
#         self.assert_cdru_result('Zipcar-3.tpn', True)
#         self.assert_cdru_result('Zipcar-4.tpn', True)
#         self.assert_cdru_result('Zipcar-5.tpn', True)
#         self.assert_cdru_result('Zipcar-6.tpn', True)
#         self.assert_cdru_result('Zipcar-7.tpn', True)
#         self.assert_cdru_result('Zipcar-8.tpn', True)
#         self.assert_cdru_result('Zipcar-9.tpn', True)
#         self.assert_cdru_result('Zipcar-10.tpn', True)
# 
    def test_max_flex_rcpsp(self):
        # self.assert_max_flex_result('PSP1.SCH1.cctp', True)
        #self.assert_max_flex_result('PSP1.SCH2.cctp', True)
        testlist = "/home/jing/workspace/testcase/list.txt"
        f = open(testlist)
        s = f.readline()
        self.ofile = open('output.txt','w')
        self.ofile.close()

        while len(s) > 1:
            s = s.replace('\n','')
            self.assert_max_flex_result(s, True)
            s = f.readline()
        self.ofile.close()
        #          self.assert_max_flex_result('PSP1.SCH3.cctp', True)
        #          self.assert_max_flex_result('PSP10.SCH1.cctp', True)
        #          self.assert_max_flex_result('PSP100.SCH1.cctp', True)
        #          self.assert_max_flex_result('PSP100.SCH2.cctp', True)
        #          self.assert_max_flex_result('PSP100.SCH3.cctp', True)

        self.assert_max_flex_result('PSP1.SCH1.cctp', True)
        self.assert_max_flex_result('PSP1.SCH2.cctp', True)
        self.assert_max_flex_result('PSP1.SCH3.cctp', True)
        self.assert_max_flex_result('PSP10.SCH1.cctp', True)
        self.assert_max_flex_result('PSP100.SCH1.cctp', True)
        self.assert_max_flex_result('PSP100.SCH2.cctp', True)
        self.assert_max_flex_result('PSP100.SCH3.cctp', True)

    def test_redline_schedule(self):
        self.assert_cdru_result('Route_Red_Headway_2_Stop_4.cctp', True)
        # self.assert_mip_result('Route_Red_Headway_2_Stop_4.cctp', True)

    def test_MIP_RCPSP(self):
        self.assert_mip_maxflex_result('PSP1.SCH3.cctp', True)

    def test_CDRU_RCPSP(self):
        # self.assert_max_flex_result('PSP1.SCH3.cctp', True)
        self.assert_max_flex_result('PSP189.SCH2.cctp', True)

    def test_CDRU_Evacuation(self):
        self.assert_max_flex_result('81r.cctp', True)

    def test_tpn_zipcar11(self):
 
        # build a kirk problem
        # first create a Tpnu
        tpnu = Tpnu('id','trip')
        # event
        # create events for this tpnu
        node_number_to_id = {}
        start_event = 1
        end_event = 2
 
        node_number_to_id[1] = 'start'
        node_number_to_id[2] = 'end'
 
        event_idx = 3
        constraint_idx = 1;
 
        # decision variable
        # create a decision variable to represent the choies over restaurants
        tpnu_decision_variable = DecisionVariable('dv','where to go?')
        tpnu.add_decision_variable(tpnu_decision_variable)
 
        # Then iterate through all goals and add them as domain assignments
        goal = 'somewhere'
        assignment = Assignment(tpnu_decision_variable, 'somewhere', 10.0)
        tpnu_decision_variable.add_domain_value(assignment)
 
        home_to_restaurant = TemporalConstraint('ep-'+str(constraint_idx), 'go to '+str(goal)+'-'+str(constraint_idx), start_event, event_idx, 36.065506858138214, 44.08006393772449)
        constraint_idx += 1
        event_idx += 1
 
        eat_at_restaurant = TemporalConstraint('ep-'+str(constraint_idx), 'dine at '+str(goal)+'-'+str(constraint_idx), event_idx-1, end_event, 0, 30)
        constraint_idx += 1
 
        node_number_to_id[event_idx-1] = 'arrive-'+str(goal)
 
        home_to_restaurant.add_guard(assignment)
        eat_at_restaurant.add_guard(assignment)
 
        tpnu.add_temporal_constraint(home_to_restaurant)
        tpnu.add_temporal_constraint(eat_at_restaurant)
 
 
        # temporal constraints
        # create constraints for the duration of the trip
        tpnu_constraint = TemporalConstraint('tc-'+str(constraint_idx), 'tc-'+str(constraint_idx), start_event, end_event, 0, 15)
        constraint_idx += 1
        tpnu_constraint.relaxable_ub = True
        tpnu_constraint.relax_cost_ub = 0.1
        tpnu.add_temporal_constraint(tpnu_constraint)
 
        tpnu.num_nodes = event_idx-1
        tpnu.node_number_to_id = node_number_to_id
 
        # next formulate a search problem using this tpnu
        search_problem = SearchProblem(tpnu,FeasibilityType.DYNAMIC_CONTROLLABILITY,ObjectiveType.MIN_COST)
        search_problem.initialize()
 
        solution = search_problem.next_solution()