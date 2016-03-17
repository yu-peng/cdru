__author__ = 'yupeng'

from tpn import Tpn
from temporal_network.tpnu import Tpnu

if __name__ == '__main__':
    # Load the tpn from file
    obj = Tpn.parseTPN(r'C:\Users\yupeng\Downloads\document.tpn')
    tpnu = Tpnu.from_tpn_autogen(obj)
