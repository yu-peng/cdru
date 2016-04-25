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
from multiprocessing import Process, Queue
from multiprocessing.managers import BaseManager
from search.candidate import Candidate

class SolverType(object):
    CDRU = 1
    MIP = 2

class MyManager(BaseManager): pass

def Manager():
    m = MyManager()
    m.start()
    return m

class SolutionContainer(object):
  def __init__(self):
    self._value = None

  def update(self, value):
    self._value = value

  def get_value(self):
      return self._value


MyManager.register('SolutionContainer', SolutionContainer, exposed = ['update', 'get_value'])

class BenchmarkRCPSP():

    @staticmethod
    def main():
        cdru_dir = dirname(__file__)
        examples_dir = join(cdru_dir, join('..', 'benchmark/MBTA/'))

        solutions = []
        for i in listdir(examples_dir):
            if i.endswith(".cctp"):
                solutionDesc = BenchmarkRCPSP.runTest(examples_dir,i,SolverType.MIP,ObjectiveType.MIN_COST)
                print(json.dumps(solutionDesc))
                solutions.append(solutionDesc)

        output = {"Results": solutions}
        print(json.dumps(output))

    @staticmethod
    def runTest(directory,file,solver,objType):
        path = join(directory, file)
        print("----------------------------------------")

        if Tpnu.isCCTP(path):
            tpnu = Tpnu.parseCCTP(path)
        elif Tpnu.isTPN(path):
            obj = Tpn.parseTPN(path)
            tpnu = Tpnu.from_tpn_autogen(obj)
        else:
            raise Exception("Input file " + path + " is neither a CCTP nor a TPN")

        startTime = datetime.now()

        manager = Manager()
        container = manager.SolutionContainer()

        p = Process(target=BenchmarkRCPSP.solve, name="Solve", args=(tpnu,solver,objType,startTime,file,container,))
        p.start()
        p.join(60)
        if p.is_alive():
            print("Solver is running... No solution found in time limit...")
            # Terminate foo
            p.terminate()
            p.join()

        solution = container.get_value()
        runtime = datetime.now() - startTime

        if solution is not None:
            print(file + " solved in " + str(runtime))
        else:
            print(file + " not solved in " + str(runtime))

        if solution is not None:
            return solution
        else:
            result = {}
            result["TestName"] = file
            result["Solver"] = BenchmarkRCPSP.getSolveName(solver)
            result["Runtime"] = runtime.total_seconds()
            result["Error"] = "No Solution Found"

            return result

    @staticmethod
    def solve(tpnu,solver,objType,startTime,filename,container):
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
        container.update(solution.json_description(filename,BenchmarkRCPSP.getSolveName(solver),runtime.total_seconds()))


    @staticmethod
    def getSolveName(solver):
        if solver == SolverType.CDRU:
            try:
                import gurobipy
                return "CDRU+GuRoBi"
            except ImportError:
                pass
            return "CDRU+PuLP"
        elif solver == SolverType.MIP:
            return "MIP+GuRoBi"
        else:
            raise Exception('Unknown solver type')

if __name__ == "__main__":
    BenchmarkRCPSP.main()