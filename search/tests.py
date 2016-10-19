
__author__ = 'yupeng'

import unittest
from os.path import join, dirname
from math import fabs
from tpn import Tpn
from temporal_network.tpnu import Tpnu, ChanceConstrained
from search.search_problem import SearchProblem
from temporal_network.tpnu import FeasibilityType, ObjectiveType
from temporal_network.decision_variable import DecisionVariable
from temporal_network.temporal_constraint import TemporalConstraint
from temporal_network.assignment import Assignment
from search.mip_encode import MipEncode
from datetime import datetime
import cProfile

class SearchTests(unittest.TestCase):
    def setUp(self):
        cdru_dir = dirname(__file__)
        self.examples_dir = join(cdru_dir, join('..', 'examples'))

    # used in most of the tests.
    def assert_cdru_result(self, example_file, f_type, o_type, c_type, expected_result):
        path = join(self.examples_dir, example_file)
        tpnu = self.getProblemFromFile(path)

        startTime = datetime.now()
        search_problem = SearchProblem(tpnu,f_type,o_type,c_type)
        search_problem.initialize()
        # pr = cProfile.Profile()
        # pr.enable()
        solution = search_problem.next_solution()
        # pr.disable()
        # # after your program ends
        # pr.print_stats(sort="cumtime")

        runtime = datetime.now() - startTime

        print("----------------------------------------")
        if solution is not None:
            print(example_file)
            solution.pretty_print()
            print(solution.json_print(example_file,"CDRU+PuLP",runtime.total_seconds(),search_problem.candidates_dequeued))

            print("Conflicts " + str(len(search_problem.known_conflicts)))
            print("Candidates " + str(search_problem.candidates_dequeued))
        else:
            print(example_file)
            print(None)
            search_problem.pretty_print()
        is_feasible = solution is not None
        self.assertEqual(is_feasible, expected_result)

    # used in most of the tests.
    def assert_mip_result(self, example_file, o_type, expected_result):
        path = join(self.examples_dir, example_file)
        tpnu = self.getProblemFromFile(path)

        startTime = datetime.now()
        mip_solver = MipEncode(tpnu,o_type)
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

    def compare_cdru_mip(self, example_file, f_type, o_type, c_type, expected_result):
        path = join(self.examples_dir, example_file)
        tpnu = self.getProblemFromFile(path)

        search_problem = SearchProblem(tpnu,f_type,o_type,c_type)
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

        tpnu = self.getProblemFromFile(path)
        mip_solver = MipEncode(tpnu,o_type)
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

    def getProblemFromFile(self, path):
        if Tpnu.isCCTP(path):
            tpnu = Tpnu.parseCCTP(path)
        elif Tpnu.isTPN(path):
            obj = Tpn.parseTPN(path)
            tpnu = Tpnu.from_tpn_autogen(obj)
        else:
            raise Exception("Input file " + path + " is neither a CCTP nor a TPN")

        return tpnu
            
    def test_cdru_basic(self):
        f_type = FeasibilityType.CONSISTENCY
        o_type = ObjectiveType.MIN_COST
        c_type = ChanceConstrained.OFF
        self.assert_cdru_result('test1.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('test2.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('test3.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('test4.tpn', f_type, o_type, c_type, True)

    def test_whoi(self):
        f_type = FeasibilityType.CONSISTENCY
        o_type = ObjectiveType.MIN_COST
        c_type = ChanceConstrained.OFF
        self.assert_cdru_result('whoi-1.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('whoi-2.cctp', f_type, o_type, c_type, True)

    def test_transit_schedule(self):
        f_type = FeasibilityType.DYNAMIC_CONTROLLABILITY
        o_type = ObjectiveType.MIN_COST
        c_type = ChanceConstrained.OFF
        self.assert_cdru_result('Route1_2_1.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('Route1_2_2.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('Route_Red_Headway_2_Stop_2.cctp', f_type, o_type, c_type, True)

    def test_bus_selection(self):
        f_type = FeasibilityType.DYNAMIC_CONTROLLABILITY
        o_type = ObjectiveType.MIN_COST
        c_type = ChanceConstrained.OFF
        self.assert_cdru_result('bus-1.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('bus-2.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('bus-3.cctp', f_type, o_type, c_type, False)
        self.assert_cdru_result('bus-4.cctp', f_type, o_type, c_type, True)
#  
    def test_cctp_zipcar(self):
        f_type = FeasibilityType.DYNAMIC_CONTROLLABILITY
        o_type = ObjectiveType.MIN_COST
        c_type = ChanceConstrained.OFF
        self.assert_cdru_result('Zipcar-1.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-10.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-3.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-4.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-5.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-8.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-9.cctp', f_type, o_type, c_type, True)

    def test_tpn_zipcar(self):
        f_type = FeasibilityType.CONSISTENCY
        o_type = ObjectiveType.MIN_COST
        c_type = ChanceConstrained.OFF
        self.assert_cdru_result('Zipcar-1.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-2.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-3.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-4.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-5.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-6.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-7.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-8.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-9.tpn', f_type, o_type, c_type, True)
        self.assert_cdru_result('Zipcar-10.tpn', f_type, o_type, c_type, True)

    def test_mip_auv(self):
        o_type = ObjectiveType.MIN_COST
        self.assert_mip_result('AUV-7.cctp', o_type, True)

    def test_max_flex_rcpsp(self):
        f_type = FeasibilityType.DYNAMIC_CONTROLLABILITY
        o_type = ObjectiveType.MAX_FLEX_UNCERTAINTY
        c_type = ChanceConstrained.OFF
        self.assert_cdru_result('PSP1.SCH1.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('PSP1.SCH2.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('PSP1.SCH3.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('PSP10.SCH1.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('PSP100.SCH1.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('PSP100.SCH2.cctp', f_type, o_type, c_type, True)
        self.assert_cdru_result('PSP100.SCH3.cctp', f_type, o_type, c_type, True)

    def test_auv_schedule(self):
        o_type = ObjectiveType.MIN_COST
        c_type = ChanceConstrained.OFF
        for f_type in [FeasibilityType.CONSISTENCY, FeasibilityType.STRONG_CONTROLLABILITY, FeasibilityType.STRONG_CONTROLLABILITY]:
            self.assert_cdru_result('AUV-1.cctp', f_type, o_type, c_type, True)
            self.assert_cdru_result('AUV-2.cctp', f_type, o_type, c_type, True)
            self.assert_cdru_result('AUV-3.cctp', f_type, o_type, c_type, True)
            self.assert_cdru_result('AUV-4.cctp', f_type, o_type, c_type, True)

    def test_auv_mip(self):
        o_type = ObjectiveType.MIN_COST
        c_type = ChanceConstrained.OFF
        f_type = FeasibilityType.CONSISTENCY
        self.assert_cdru_result('AUV-4.cctp', f_type, o_type, c_type, True)

    def test_auv_cc_schedule(self):
        f_type = FeasibilityType.DYNAMIC_CONTROLLABILITY
        o_type = ObjectiveType.MIN_COST
        c_type = ChanceConstrained.ON
        self.assert_cdru_result('AUV-2364.cctp', f_type, o_type, c_type, True)
        # self.assert_cdru_result('AUV-1.cctp', f_type, o_type, c_type, True)
        # self.assert_cdru_result('AUV-2.cctp', f_type, o_type, c_type, True)
        # self.assert_cdru_result('AUV-3.cctp', f_type, o_type, c_type, True)
        # self.assert_cdru_result('AUV-4.cctp', f_type, o_type, c_type, True)
        # self.assert_cdru_result('AUV-10.cctp', f_type, o_type, c_type, True)
        # self.assert_cdru_result('AUV-24.cctp', f_type, o_type, c_type, True)
        # self.assert_cdru_result('AUV-100.cctp', f_type, o_type, c_type, True)
        # self.assert_cdru_result('AUV-105.cctp', f_type, o_type, c_type, True)
        # self.assert_cdru_result('AUV-1000.cctp', f_type, o_type, c_type, True)

    def test_mip_rcpsp(self):
        o_type = ObjectiveType.MAX_FLEX_UNCERTAINTY
        self.assert_cdru_result('PSP1.SCH1.cctp', o_type, True)
        self.assert_cdru_result('PSP1.SCH2.cctp', o_type, True)
        self.assert_cdru_result('PSP1.SCH3.cctp', o_type, True)
        self.assert_cdru_result('PSP10.SCH1.cctp', o_type, True)
        self.assert_cdru_result('PSP100.SCH1.cctp', o_type, True)
        self.assert_cdru_result('PSP100.SCH2.cctp', o_type, True)
        self.assert_cdru_result('PSP100.SCH3.cctp', o_type, True)

    def test_CDRU_Evacuation(self):
        f_type = FeasibilityType.DYNAMIC_CONTROLLABILITY
        o_type = ObjectiveType.MAX_FLEX_UNCERTAINTY
        c_type = ChanceConstrained.OFF
        self.assert_cdru_result('81r.cctp', f_type, o_type, c_type, True)