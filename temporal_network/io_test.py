__author__ = 'yupeng'

import unittest
from os.path import join, dirname

from tpn import Tpn
from temporal_network.tpnu import Tpnu

class TpnuParserTests(unittest.TestCase):
    def setUp(self):
            cdru_dir = dirname(__file__)
            self.examples_dir = join(cdru_dir, join('..', 'examples'))

    def assert_cctp_result(self, example_file, expected_result):

        obj = Tpnu.parseCCTP(join(self.examples_dir, example_file))
        if obj is not None:
            self.assertEqual(expected_result, True)

        if obj is None:
            self.assertEqual(expected_result, False)

    def assert_tpn_result(self, example_file, expected_result):

        tpn_obj = Tpn.parseTPN(join(self.examples_dir, example_file))
        tpnu_obj = Tpnu.from_tpn_autogen(tpn_obj)

        if tpnu_obj is not None:
            self.assertEqual(expected_result, True)

        if tpnu_obj is None:
            self.assertEqual(expected_result, False)

    def test_cctp1(self):
        self.assert_cctp_result('Route1_2_2.cctp', True)

    def test_cctp2(self):
        self.assert_cctp_result('2g2a.cctp', True)

    def test_tpn1(self):
        self.assert_tpn_result('test1.tpn', True)