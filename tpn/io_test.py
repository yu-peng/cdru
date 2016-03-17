__author__ = 'yupeng'

from tpn import Tpn


if __name__ == '__main__':
    # Load the tpn from file
    obj = Tpn.parseTPN(r'C:\Users\yupeng\Downloads\document.tpn')
    print("TPN parsed successfully")
    Tpn.writeTPN(obj, r'C:\Users\yupeng\Downloads\document_out.tpn')