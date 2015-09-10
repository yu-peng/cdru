__author__ = 'yupeng'

from tpn import Tpn


if __name__ == '__main__':
    # Load the tpn from file
    obj = Tpn.parse(r'C:\Users\yupeng\Downloads\document.tpn')
    print("TPN parsed successfully")
    Tpn.write(obj, r'C:\Users\yupeng\Downloads\document_out.tpn')