import unittest
from os.path import join, dirname

from tpn import Tpn
from temporal_network.tpnu import Tpnu
from controllability.dynamic_controllability import DynamicControllability
from temporal_network.stnu import Stnu, StnuEdge
from search.conflict import Conflict


class ControllabilityTests(unittest.TestCase):
    def setUp(self):
        controllability_dir = dirname(__file__)
        self.examples_dir = join(controllability_dir, join('..', 'examples'))

    def assert_dc_result(self, example_file, expected_result):
        for solver in DynamicControllability.SOLVERS:

            path = join(self.examples_dir, example_file)

            if Tpnu.isCCTP(path):
                tpnu = Tpnu.parseCCTP(path)
            elif Tpnu.isTPN(path):
                obj = Tpn.parseTPN(join(self.examples_dir, example_file))
                tpnu = Tpnu.from_tpn_autogen(obj)
            else:
                raise Exception("Input file " + path + " is neither a CCTP nor a TPN")

            # for tc in tpnu.temporal_constraints:
            #     tpnu.temporal_constraints[tc].pretty_print()

            conflict = DynamicControllability.check(tpnu, solver=solver)

            # if conflict is not None:
            #     kirk_conflict = Conflict()
            #     kirk_conflict.add_negative_cycles(conflict,tpnu)
            #     kirk_conflict.pretty_print()

            is_dynamically_controllable = conflict is None
            self.assertEqual(is_dynamically_controllable, expected_result)

    def test_dc1(self):
        self.assert_dc_result('test1.tpn', True)

    def test_dc2(self):
        self.assert_dc_result('test2.tpn', False)

    def test_dc3(self):
        self.assert_dc_result('test3.tpn', True)

    def test_dc4(self):
        self.assert_dc_result('test4.tpn', False)

    def test_dc5(self):
        self.assert_dc_result('ControllabilityTest.tpn', False)

    def test_dc6(self):
        self.assert_dc_result('Route1_2_1.cctp', False)

    def test_dc7(self):
        self.assert_dc_result('Route1_2_2.cctp', False)

    def test_nozeronode(self):
        with self.assertRaises(Exception):
            stnu = Stnu()
            stnu.num_nodes = 1
            stnu.controllable_edges.append(StnuEdge(0, 1, 100, 200, 'my-id'))
            DynamicControllability.check(stnu, solver='morris_n4_dc')