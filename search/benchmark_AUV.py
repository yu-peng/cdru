__author__ = 'yupeng'

from os.path import join, dirname
from os import listdir
import json
from math import fabs
from tpn import Tpn
from temporal_network.tpnu import Tpnu, ChanceConstrained
from search.search_problem import SearchProblem
from temporal_network.tpnu import FeasibilityType, ObjectiveType
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

class BenchmarkAUV():

    @staticmethod
    def main():

        f_type = FeasibilityType.DYNAMIC_CONTROLLABILITY
        o_type = ObjectiveType.MIN_COST
        c_type = ChanceConstrained.ON

        cdru_dir = dirname(__file__)
        # examples_dir = join(cdru_dir, join('..', 'benchmark/MBTA/'))
        # examples_dir = 'E:/Dropbox/Code/Algorithms/TestGenerator/tests/AUV/'
        # examples_dir = 'C:/Users/yupeng/Dropbox/Code/Algorithms/TestGenerator/tests/AUV/'
        # examples_dir = 'F:/BenchmarkCases/JAIR 2015/AUV/'
        examples_dir = '/home/yupeng/Documents/AUV/'

        solutions = []
        for i in listdir(examples_dir):
            if i.endswith(".cctp"):
                solutionDesc = BenchmarkAUV.runTest(examples_dir,i,SolverType.CDRU,o_type,f_type,c_type)
                # print(json.dumps(solutionDesc))
                solutions.append(solutionDesc)

        output = {"Results": solutions}
        text_file = open(examples_dir+"results-"+str(datetime.now().date())+".txt", "w")
        text_file.write(json.dumps(output))
        text_file.close()
        # print(json.dumps(output))

    @staticmethod
    def runTest(directory,file,solver,objType,feaType,ccType):
        path = join(directory, file)
        print("----------------------------------------")
        print("Solving: " + file)

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

        p = Process(target=BenchmarkAUV.solve, name="Solve", args=(tpnu,solver,objType,feaType,ccType,startTime,file,container,))
        p.start()
        p.join(30)
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
            result["Solver"] = BenchmarkAUV.getSolveName(solver)
            result["Runtime"] = runtime.total_seconds()
            result["Error"] = "No Solution Found"

            return result

    @staticmethod
    def solve(tpnu,solver,objType,feaType,ccType,startTime,filename,container):
        if solver == SolverType.CDRU:
            search_problem = SearchProblem(tpnu,feaType,objType,ccType)
            search_problem.initialize()
            solution = search_problem.next_solution()
        elif solver == SolverType.MIP:
            mip_solver = MipEncode(tpnu,objType)
            solution = mip_solver.mip_solver()
        else:
            raise Exception('Unknown solver type')

        runtime = datetime.now() - startTime
        container.update(solution.json_description(filename,BenchmarkAUV.getSolveName(solver),runtime.total_seconds(),search_problem.candidates_dequeued))


    @staticmethod
    def getSolveName(solver):
        if solver == SolverType.CDRU:
            try:
                import gurobipy
                return "CDRU+GuRoBi"
            except ImportError:
                pass
            # return "CDRU+PuLP"
            return "CDRU+SNOPT"
        elif solver == SolverType.MIP:
            return "MIP+GuRoBi"
        else:
            raise Exception('Unknown solver type')

if __name__ == "__main__":
    BenchmarkAUV.main()