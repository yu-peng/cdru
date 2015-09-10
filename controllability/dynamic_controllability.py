from controllability.morris_n4_dc import MorrisN4Dc
from temporal_network.tpnu import Tpnu
from tpn.tpn_autogen import tpn as ParseTpnClass

class DynamicControllability(object):
    SOLVERS = [
        'morris_n4_dc'
    ]

    @staticmethod
    def check(network, solver='morris_n4_dc'):
        if solver == 'morris_n4_dc':
            alg = MorrisN4Dc()
            if type(network) == ParseTpnClass:
                network = Tpnu.from_tpn_autogen(network)
                network.initialize()
            elif type(network) == Tpnu:
                pass
            else:
                raise Exception("Wrong type of network passed to dc checking")

            return alg.check(network)

        else:
            raise Exception('Unknown dynamic controllability solver')

