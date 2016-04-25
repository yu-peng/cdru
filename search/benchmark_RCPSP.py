__author__ = 'yupeng'

from os.path import join, dirname
from os import listdir
import json
from math import fabs
from tpn import Tpn
from temporal_network.tpnu import Tpnu
from search.search_problem import SearchProblem, FeasibilityType, ObjectiveType
from datetime import datetime
from search.mip_encode import MipEncode

class SolverType(object):
    CDRU = 1
    MIP = 2

class BenchmarkRCPSP():

    @staticmethod
    def main():
        cdru_dir = dirname(__file__)
        examples_dir = join(cdru_dir, join('..', 'benchmark/RCPSP/J10/'))

        solutions = []
        for i in listdir(examples_dir):
            if i.endswith(".cctp"):
                solutionDesc = BenchmarkRCPSP.runTest(examples_dir,i,SolverType.CDRU,ObjectiveType.MAX_FLEX_UNCERTAINTY)
                print(json.dumps(solutionDesc))
                solutions.append(solutionDesc)

        output = {"Results": solutions}
        print(json.dumps(output))

    @staticmethod
    def runTest(directory,file,solver,objType):
        path = join(directory, file)

        if Tpnu.isCCTP(path):
            tpnu = Tpnu.parseCCTP(path)
        elif Tpnu.isTPN(path):
            obj = Tpn.parseTPN(path)
            tpnu = Tpnu.from_tpn_autogen(obj)
        else:
            raise Exception("Input file " + path + " is neither a CCTP nor a TPN")

        startTime = datetime.now()
        if solver == SolverType.CDRU:
            search_problem = SearchProblem(tpnu,FeasibilityType.DYNAMIC_CONTROLLABILITY,objType)
            search_problem.initialize()
            solution = search_problem.next_solution()
        elif solver == SolverType.MIP:
            mip_solver = MipEncode(tpnu,objType)
            solution = mip_solver.mip_solver()
        else:
            raise Exception('Unknown solver type')

        runtime = datetime.now() - startTime

        print("----------------------------------------")
        if solution is not None:
            print(file + " solved in " + str(runtime))
        else:
            print(file + " not solved in " + str(runtime))

        return solution.json_description(file,"CDRU+PuLP",runtime.total_seconds())

if __name__ == "__main__":
    BenchmarkRCPSP.main()