from gurobipy import *
from temporal_network.tpnu import Tpnu
from tpn.tpn_autogen import tpn as ParseTpnClass
from friends.utils.logging import initialize
from search.candidate import Candidate
from search.temporal_relaxation import TemporalRelaxation
from temporal_network.temporal_constraint import TemporalConstraint

class MipEncode(object):
    
    def __init__(self, tpnu):
        self.network = tpnu
        self.initialize()
       # self.mip_solver()
        
    def initialize(self):
        if type(self.network) == ParseTpnClass:
            self.network = Tpnu.from_tpn_autogen(self.network)
        elif type(self.network) == Tpnu:
            pass
        else:
            raise Exception("Wrong type of network passed to MIP encode")
        self.network.initialize()
        self.num_nodes = self.network.num_nodes
        self.l = {}  # lower bounds
        self.u = {}  # upper bounds
        self.w = {}  # wait
        self.b = {}  # binary variables
        self.x = {}  # binary variables
        self.calc_distance()
        
    def calc_distance(self):
        self.dis = {}
        for node_a in range(1, self.num_nodes + 1):
            for node_b in range(node_a + 1, self.num_nodes + 1):
                self.dis[(node_a, node_b)] = self.dis[(node_b, node_a)] = (-100000, 100000)
        for e in self.network.temporal_constraints.values():
            if e.controllable:
                self.dis[(e.fro, e.to)] = (e.get_lower_bound(), e.get_upper_bound())
                self.dis[(e.to, e.fro)] = (-e.get_upper_bound(), -e.get_lower_bound())
            else:
                self.dis[(e.fro, e.to)] = (e.get_lower_bound(), e.get_upper_bound())
                #self.dis[(e.to, e.fro)] = (-e.get_upper_bound(), -e.get_lower_bound())
        return  
        for node_k in range(1, self.num_nodes + 1):
            for node_i in range(1, self.num_nodes + 1):
                for node_j in range(1, self.num_nodes + 1):
                    if node_i != node_j and node_i != node_k and node_j != node_k:
#                         print(self.dis[(node_i, node_k)] )
#                         print(self.dis[(node_k, node_j)])
                        new_lb = self.dis[(node_i, node_k)][0] + self.dis[(node_k, node_j)][0]
                        new_ub = self.dis[(node_i, node_k)][1] + self.dis[(node_k, node_j)][1]
                        if new_lb < self.dis[(node_i, node_j)][0]:
                            new_lb = self.dis[(node_i, node_j)][0]
                        if new_ub > self.dis[(node_i, node_j)][1]:
                            new_ub = self.dis[(node_i, node_j)][1]
                        self.dis[(node_i, node_j)] = (new_lb, new_ub)
                    
        
    def next_solution(self):
        return self.mip_solver()
        
    def wait_reduce(self, e):
        for node_id in range(1, self.num_nodes+1):
            self.v_set[node_id] = 0
        self.v_set[e.fro] = 3
        self.v_set[e.to] = 3
            
    def add_vars(self, m):
        
        # add the extra variable to represent minimum delay
        self.Z = m.addVar(vtype=GRB.CONTINUOUS, lb=.1, name = "Z")
        
        # add variables for links
        self.encoded_node_pairs = {}
        K = 0

        for e in self.network.temporal_constraints.values():
            # We only consider constraints that are active
            if e.activated:
                if e.fro == 0 or e.to == 0:
                    raise Exception("Node with id zero is not allowed (see documentation for check function.)")
                # print('%s-%s(%s)[%s,%s]'%(e.fro,e.to,e.controllable, e.get_lower_bound(), e.get_upper_bound()))
                if e.controllable:
                    
                    # Make sure no two edges share the same from and to nodes
                    if (e.fro, e.to) not in self.encoded_node_pairs:
                        # add_controllable(e.fro,e.to,e.get_lower_bound(),e.get_upper_bound(),e.id)
                        self.l[(e.fro, e.to)] = m.addVar(lb=e.get_lower_bound(), ub=e.get_upper_bound(), vtype=GRB.CONTINUOUS, name="l_%s_%s" % (e.fro, e.to))
                        self.u[(e.fro, e.to)] = m.addVar(lb=e.get_lower_bound(), ub=e.get_upper_bound(), vtype=GRB.CONTINUOUS, name="u_%s_%s" % (e.fro, e.to))
                        self.encoded_node_pairs[(e.fro, e.to)] = True
                        self.encoded_node_pairs[(e.to, e.fro)] = True
                        m.update()
                        # the opposite direction
                        self.l[(e.to, e.fro)] = -self.u[(e.fro, e.to)]
                        self.u[(e.to, e.fro)] = -self.l[(e.fro, e.to)]
                    else:
                        sdf = 1
                        # update the bounds of the variables if there are multiple links between e.fro and e.to
#                         lb = self.l[(e.fro, e.to)].getAttr(GRB.Attr.LB)
#                         ub = self.l[(e.fro, e.to)].ub
#                         if lb > e.get_lower_bound(): lb = e.get_lower_bound()
#                         if ub < e.get_upper_bound(): ub = e.get_upper_bound()
#                         self.l[(e.fro, e.to)].lb = lb
#                         self.u[(e.fro, e.to)].lb = lb
#                         self.l[(e.fro, e.to)].ub = ub
#                         self.u[(e.fro, e.to)].ub = ub
#                         new_node = num_nodes + 1
#                         num_nodes += 1
                        
                       # print("Temp")
#                         self.network.temporal_constraints.pop(e)
#                         self.network.temporal_constraints.
#                         self.l[(e.fro, new_node)] = m.addVar(lb = e.get_lower_bound(), ub = e.get_upper_bound(), vtype = GRB.CONTINUOUS, name = "l_%s_%s"%(e.fro,new_node))
#                         self.u[(e.fro, new_node)] = m.addVar(lb = e.get_lower_bound(), ub = e.get_upper_bound(), vtype = GRB.CONTINUOUS, name = "u_%s_%s"%(e.fro,new_node))
#                         self.encoded_node_pairs[(e.fro,new_node)] = True
#                         self.l[(new_node, e.to)] = m.addVar(lb = 0, ub = 0, vtype = GRB.CONTINUOUS, name = "l_%s_%s"%(new_node,e.to))
#                         self.u[(new_node, e.to)] = m.addVar(lb = 0, ub = 0, vtype = GRB.CONTINUOUS, name = "u_%s_%s"%(new_node,e.to))
#                         self.encoded_node_pairs[(e.fro,e.to)] = True
#                         renaming[new_node] = renaming[e.to] + "'"
#                         add_controllable(e.fro,new_node,e.get_lower_bound(),e.get_upper_bound(),e.id)
#                         add_controllable(new_node,e.to,0,0,None)
                else:
                    K += 1
                    #print(e.fro, e.to, e.name, e.get_lower_bound(), e.get_upper_bound())
                    if e.relaxable_lb == True:
                        self.l[(e.fro, e.to)] = m.addVar(lb=e.get_lower_bound(), ub=e.get_upper_bound(), vtype=GRB.CONTINUOUS, name=e.name + "l")
                    else:
                        self.l[(e.fro, e.to)] = e.get_lower_bound()
                    if e.relaxable_ub == True:
                        self.u[(e.fro, e.to)] = m.addVar(lb=e.get_lower_bound(), ub=e.get_upper_bound(), vtype=GRB.CONTINUOUS, name=e.name + "u")
                    else:
                        self.u[(e.fro, e.to)] = e.get_upper_bound()                                                
                    self.encoded_node_pairs[(e.fro, e.to)] = True
                    
                    m.update()
                    # the opposite direction
                    self.l[(e.to, e.fro)] = -self.u[(e.fro, e.to)]
                    self.u[(e.to, e.fro)] = -self.l[(e.fro, e.to)]
                    self.encoded_node_pairs[(e.to, e.fro)] = True
                        # contingent edges with bounds [l, u] can be normalized to edge
                        # can be replaced by requirement edge [l,l] followed by upper case edge
                        # new_node = num_nodes + 1
                        # num_nodes += 1
                        # print('temp\n')
                        # renaming[new_node] = renaming[e.fro] + "'"
                        # add_uncontrollable(e.fro, new_node, e.to, e.get_lower_bound(), e.get_upper_bound(), e.id)

        
    def add_constrs(self, m):
        
        for e in self.network.temporal_constraints.values():
            # We only consider constraints that are active
            if e.activated:
                if e.fro == 0 or e.to == 0:
                    raise Exception("Node with id zero is not allowed (see documentation for check function.)")
                
                # print('%s-%s(%s)[%s,%s]'%(e.fro,e.to,e.controllable, e.get_lower_bound(), e.get_upper_bound()))
                # add l <= u
                # if self.l[(e.fro, e.to)] - self.u[(e.fro, e.to)] != None:
                m.addConstr(self.l[(e.fro, e.to)] - self.u[(e.fro, e.to)] <= 0, "c%s_%s" % (e.fro, e.to))
                
                # add wait and precede constraints according to contingent links
                if e.controllable == False:  
                    
                    # add z <= u - l
                    m.addConstr(self.Z <= self.u[(e.fro, e.to)] - self.l[(e.fro, e.to)], "cz%s_%s" % (e.fro, e.to))               

                    # add links repeatedly until no update
                    added_pairs = {}
                    wait_pair = {}
                    b_update = True
                    while b_update == True:
                        b_update = False
                        
                        # find necessary nodes to add links and mark the nodes by v_set
                        self.v_set = {}
                        self.wait_reduce(e)
                       # print(self.v_set[e.fro],self.v_set[e.to])
                        
                        # add variables and constraints for the added links
                        for node_id in range(1, self.num_nodes):
                            if node_id != e.fro and node_id != e.to:
                                if self.v_set[node_id] == 0:
                                    if (e.fro, node_id) not in self.encoded_node_pairs:
                                        self.add_var_rqm(m, e.fro, node_id)
#                                         self.l[(e.fro, node_id)] = m.addVar(vtype=GRB.CONTINUOUS, name="l_%s_%s" % (e.fro, node_id))
#                                         self.u[(e.fro, node_id)] = m.addVar(vtype=GRB.CONTINUOUS, name="u_%s_%s" % (e.fro, node_id))
#                                         added_pairs[(e.fro, node_id)] = True
#                                         self.encoded_node_pairs[(e.fro, node_id)] = True
                                        b_update = True
#                                         m.update()
#                                         # the opposite direction
#                                         self.l[(node_id, e.fro)] = -self.u[(e.fro, node_id)]
#                                         self.u[(node_id, e.fro)] = -self.l[(e.fro, node_id)]
#                                         self.encoded_node_pairs[(node_id, e.fro)] = True
                                    if (node_id, e.to) not in self.encoded_node_pairs:
                                        b_update = True
                                        added_pairs[(node_id, e.to)] = True
                                        self.add_var_rqm(m, node_id, e.to)
#                                         self.l[(node_id, e.to)] = m.addVar(vtype=GRB.CONTINUOUS, name="l_%s_%s" % (node_id, e.to))
#                                         self.u[(node_id, e.to)] = m.addVar(vtype=GRB.CONTINUOUS, name="u_%s_%s" % (node_id, e.to))
#                                         
#                                         self.encoded_node_pairs[(node_id, e.to)] = True
# 
#                                         m.update()
#                                         
#                                         # the opposite direction
#                                         self.l[(e.to, node_id)] = -self.u[(node_id, e.to)]
#                                         self.u[(e.to, node_id)] = -self.l[(node_id, e.to)]
#                                         self.encoded_node_pairs[(e.to, node_id)] = True   
                                    if (e.fro, node_id) not in wait_pair:
                                        # add wait variable
                                        self.w[(e.fro, node_id)] = m.addVar(lb = self.dis[(e.fro, node_id)][0], vtype=GRB.CONTINUOUS, name="w_%s_%s" % (e.fro, node_id))
                                        # add binary variable wab - lac >= 0
                                        self.b[(e.fro, node_id)] = m.addVar(vtype=GRB.BINARY, name="b_%s_%s" % (e.fro, node_id))
                                        # add binary variable lbc >= 0
                                        self.x[(node_id, e.to)] = m.addVar(vtype = GRB.BINARY, name = "x_%s_%s" % (node_id, e.to))
                                        wait_pair[(e.fro, node_id)] = True
                    
                    m.update()
                    
                    for (node_a, node_b) in added_pairs:
                        # l <= u
                        m.addConstr(self.l[(node_a, node_b)] <= self.u[(node_a, node_b)], "c%s_%s" % (node_a, node_b))
                    
                    for (node_a, node_b) in wait_pair:
                        # l <= w <= u
                        m.addConstr(self.l[(node_a, node_b)] <= self.w[(node_a, node_b)], "wb%s_%s_l" % (node_a, node_b))
                        m.addConstr(self.w[(node_a, node_b)] <= self.u[(node_a, node_b)], "wb%s_%s_u" % (node_a, node_b))                                
                        
                        # triangular wait
                        m.addConstr(self.w[(node_a, node_b)] >= self.u[(e.fro, e.to)] - self.u[(node_b, e.to)], "triw%s_%s" % (node_a, node_b))
                        
                        # add regression waits
                        for e1 in self.network.temporal_constraints.values():
                            if e1.to == node_b and (node_a, e1.fro) in wait_pair:
                                # if wab >= lac, wad >= wab - ldb
                                m.addConstr(self.w[(node_a, e1.fro)] - self.w[(node_a, node_b)] + self.l[(e1.fro, e1.to)] - 
                                            (1 - self.b[(node_a, node_b)]) * (-GRB.INFINITY) >= 0 , "rew%s_%s"%(node_a, e1.fro))
                                break
                            
                        # add wait bounds
                        # wab - lac + (x-1) * L>=0
                        m.addConstr(self.w[(node_a, node_b)] - self.l[(e.fro, e.to)] + (self.b[(node_a, node_b)] - 1) * (-GRB.INFINITY) >= 1, "wb1_%s_%s"%(node_a, node_b))
                        # wab - lac - x * U <=0
                        m.addConstr(self.w[(node_a, node_b)] - self.l[(e.fro, e.to)] - self.b[(node_a, node_b)] * (GRB.INFINITY) <= 0, "wb2_%s_%s"%(node_a, node_b))
                        # lab - lac + (x-1) * L >=0
                        m.addConstr(self.l[(node_a, node_b)] - self.l[(e.fro, e.to)] + (self.b[(node_a, node_b)] - 1) * (-GRB.INFINITY) >= 0, "wb3_%s_%s"%(node_a, node_b))
                        # lab - wab - x * L >= 0
                        m.addConstr(self.l[(node_a, node_b)] - self.w[(node_a, node_b)] - self.b[(node_a, node_b)] * (-GRB.INFINITY) >= 0, "wb4_%s_%s"%(node_a, node_b))
                  
                        # precede constraints
                        A = e.fro
                        C = e.to
                        B = node_b
                       # print(A, B, C)
                        if self.dis[(B, C)][0] > 0 and self.dis[(B, C)][1] > 0:
                        # if True:
                            # lab = uac - ubc
                            m.addConstr(self.l[(A, B)] == self.u[(A, C)] - self.u[(B, C)], "pl%s_%s" % (A, B))
                            # uab = lac - lbc
                            m.addConstr(self.u[(A, B)] == self.l[(A, C)] - self.l[(B, C)], "pu%s_%s" % (A, B))
                        elif self.dis[(B, C)][1] > 0:
                            m.addConstr(self.x[(B, C)] * (self.l[(A, B)] - self.u[(e.fro, e.to)] + self.u[(B, e.to)]) >= 0, "pbl%s_%s" % (A, B))
                            m.addConstr(self.x[(B, C)] * (self.u[(A, B)] - self.l[(e.fro, e.to)] + self.l[(B, e.to)]) <= 0, "pbu%s_%s" % (A, B))
                            # lbc - xU <= 0
                            m.addConstr(self.l[(B, C)] - self.x[(B, C)] * self.dis[(B, C)][1] <= 0, "pbxu%s_%s" % (A, B))
                            # lbc + (x-1)(L-1) > 0
                            m.addConstr(self.l[(B, C)] + (self.x[(B, C)] - 1) * (self.dis[(B, C)][0] - 1e-6) >= 1e-6, "pbxl%s_%s" % (A , B))
                                                
                            
                            
                            
    def add_var_rqm(self, m, fro, to):
        self.l[(fro, to)] = m.addVar(lb = self.dis[(fro, to)][0], ub = self.dis[(fro, to)][1], vtype=GRB.CONTINUOUS, name="l_%s_%s" % (fro, to))
        self.u[(fro, to)] = m.addVar(lb = self.dis[(fro, to)][0], ub = self.dis[(fro, to)][1], vtype=GRB.CONTINUOUS, name="u_%s_%s" % (fro, to))
        self.encoded_node_pairs[(fro, to)] = True
        m.update()
        # the opposite direction
        self.l[(to, fro)] = -self.u[(fro, to)]
        self.u[(to, fro)] = -self.l[(fro, to)]
        self.encoded_node_pairs[(to, fro)] = True                                                                                            
                        
    def add_spc(self, m):
        
        cnt = {}
        b_del = {}
        for node_a in range(1, self.num_nodes + 1):
            cnt1 = 0
            b_del[node_a] = True
            adjacent = []
            for node_b in range(1, self.num_nodes + 1):
                if node_a != node_b and (node_a, node_b) in self.encoded_node_pairs:
                    cnt1 = cnt1 + 1
                    adjacent.append(node_b)
            cnt2 = 0
            for node_b in adjacent:
                for node_c in adjacent:
                    if node_b != node_c and (node_c, node_b) in self.encoded_node_pairs:
                        cnt2 = cnt2 + 1
            cnt[node_a] = 1.0 * cnt2 / cnt1                       
                        
        for round_id in range(1, self.num_nodes):
            next_node = 0
            for node_id in range(1, self.num_nodes + 1):
                if b_del[node_id] and (next_node == 0 or cnt[next_node] < cnt[node_id]):
                    next_node = node_id                                 
            
            #print(round_id, next_node)
            adjacent = []
            for node_id in range(1, self.num_nodes + 1):
                if b_del[node_id] and (node_id, next_node) in self.encoded_node_pairs:
                    adjacent.append(node_id)
            
            b_del[next_node] = False
            
            A = next_node
            for B in adjacent:
                for C in adjacent:
                    if B != C:
                        # add shortest path constraints
                        if (B, C) not in self.encoded_node_pairs :
                            #print("add edge")
                            self.add_var_rqm(m, B, C)
                            m.update()
                        
                        # lac <= lab + ubc
                        m.addConstr(self.l[(A, C)] - self.u[(A, B)] - self.l[(B, C)] <= 0, "sp1_%s_%s_%s" % (A, B, C))
                        # lac <= uab + lac
                        m.addConstr(self.l[(A, C)] - self.l[(A, B)] - self.u[(B, C)] <= 0, "sp2_%s_%s_%s" % (A, B, C))
                        # lab + ubc <= uac
                        m.addConstr(self.u[(A, C)] - self.l[(A, B)] - self.u[(B, C)] >= 0, "sp3_%s_%s_%s" % (A, B, C))
                        # uab + lbc <= uac
                        m.addConstr(self.u[(A, C)] - self.u[(A, B)] - self.l[(B, C)] >= 0, "sp4_%s_%s_%s" % (A, B, C))
                        # uac <= uab + ubc
                        m.addConstr(self.u[(A, C)] - self.u[(A, B)] - self.u[(B, C)] <= 0, "sp5_%s_%s_%s" % (A, B, C))
                        # lac >= lab + lbc 
                        m.addConstr(self.l[(A, C)] - self.l[(A, B)] - self.l[(B, C)] >= 0, "sp6_%s_%s_%s" % (A, B, C))
                        
    def get_solution(self, m):                    
        solution = Candidate()
        
        for var_a in m.getVars():
            vname = var_a.getAttr(GRB.Attr.VarName)
            for e in self.network.temporal_constraints.values():
                if e.controllable:
                    continue

                if vname.find(e.name) != -1:
                    #print(vname, e.name)
                    new_relaxation = TemporalRelaxation(e)
                    if vname.find("l") != -1:
                        new_relaxation.relaxed_lb = var_a.getAttr("X")
                        if new_relaxation.relaxed_lb != e.get_lower_bound():
                            solution.add_temporal_relaxation(new_relaxation)                            
                    else :
                        new_relaxation.relaxed_ub = var_a.getAttr("X")
                        if new_relaxation.relaxed_ub != e.get_upper_bound():
                            solution.add_temporal_relaxation(new_relaxation)                        
                    
        solution.utility = m.getObjective().getValue()
        return solution     
        
    def mip_solver(self):
        
        try:
            
            # create a new model
            m = Model("mip_solver")
            #m.params.outputflag = 1
            # add variables
            self.add_vars(m)
            
            # integrate new variables
            m.update()
            print("add constr")
            m.setObjective(self.Z+0.0, GRB.MAXIMIZE)
            # add constraints
            self.add_constrs(m)
            self.add_spc(m)
            

            m.write("1.lp")
            m.update()
            m.optimize()
            
            if m.status == GRB.Status.INF_OR_UNBD:
                m.setParam(GRB.Param.Presolve, 0)
                m.optimize()
            
            if m.status == GRB.Status.OPTIMAL:
                m.write("1.sol")
                m.fixed()
                return self.get_solution(m)
            if m.status != GRB.Status.INFEASIBLE:
                print(m.status)
            m.computeIIS()
            m.write("1.ilp")
            
        except GurobiError as e:
            print('Error reported')
            print (e.message)


