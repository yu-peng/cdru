import unittest

from graph_theory.spfa import spfa


class GraphTheoryTests(unittest.TestCase):
    def setUp(self):
        source = 0
        num_nodes = 5
        neighbour_list = [[1], # 0
                          [2], # 1
                          [3], # 2
                          [4, 1], # 3
                          [1], # 4
                         ]
        weights = {(0,1): 20,
                   (1,2) : 1,
                   (2,3) : 2,
                   (3,4) : -2,
                   (4, 1): -1,
                   (3, 1): -4,
                   }
        self.example_graph = (source, num_nodes, weights, neighbour_list)
        self.example_graph_cycle = [1,2,3]

    def is_cyclicily_equal(self, list1, list2):
        if len(list1) != len(list2):
            return False

        n = len(list1)

        for shift in range(n):
            if list1 == list2[shift:] + list2[:shift]:
                return True

        return False


    def test_negative_cycle(self):
        _, negative_cycle = spfa(*self.example_graph)
        # Careful, double negation ahead
        assert(negative_cycle is not None)
        assert(self.is_cyclicily_equal(negative_cycle, self.example_graph_cycle))
