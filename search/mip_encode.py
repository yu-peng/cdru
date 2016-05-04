from gurobipy import *
from temporal_network.tpnu import Tpnu
from tpn.tpn_autogen import tpn as ParseTpnClass, guard
# from friends.utils.logging import initialize
from search.candidate import Candidate
from search.temporal_relaxation import TemporalRelaxation
from temporal_network.temporal_constraint import TemporalConstraint
from search.search_problem import ObjectiveType

class MipEncode(object):
    
    def __init__(self, tpnu, obj_type):
        self.network = tpnu
        self.objective_type = obj_type;
        self.DEFAULT = 100000
        self.estimate_default()
        
        # no two links share the same end nodes
        pair_nodes = {}
        v_new_constraint = {}
        b_end_unc = {}
        for e in self.network.temporal_constraints.values():
           # print(e.fro, e.to, e.get_lower_bound(), e.get_upper_bound(),e.controllable)
            if e.controllable:
                if e.get_upper_bound() > self.DEFAULT:
                    self.network.temporal_constraints[e.id].upper_bound = self.DEFAULT
                if (e.fro, e.to) in pair_nodes:
                    #print("o", e.fro, e.to)
                    new_node = self.network.num_nodes+1
                    self.network.num_nodes+=1
                    new_constraint = TemporalConstraint(new_node, new_node, e.fro, new_node, 0,0)
                    self.network.temporal_constraints[e.id].fro = new_node
                    v_new_constraint[new_constraint.id] = new_constraint
                    #print("s",new_constraint.fro,new_constraint.to, e.fro, e.to)
#                    self.network.add_temporal_constraint(new_constraint)
                pair_nodes[(e.fro, e.to)] = True
            else:
                #print(e.to)
                b_end_unc[e.to] = True
        
        for e in self.network.temporal_constraints.values():
            if not e.controllable and e.fro in b_end_unc:
                    new_node = self.network.num_nodes+1
                    self.network.num_nodes+=1
                    new_constraint = TemporalConstraint(new_node, new_node, e.fro, new_node, 0,0)
                    self.network.temporal_constraints[e.id].fro = new_node
                    v_new_constraint[new_constraint.id] = new_constraint
            
        
        for e in v_new_constraint.values():
            self.network.add_temporal_constraint(e)
        self.initialize()
        
        #print a dot file
       # f = open('1.dot', 'w')
      #  f.write('digraph G {\n nodesep = .45; \n size = 30;\n label="CCTP";\n')
         
      #  for e in self.network.temporal_constraints.values():
      #      if e.activated:
       #         f.write('"%s"->"%s"[ label = "[%s,%s] %d"];'%(e.fro, e.to,e.get_lower_bound(),e.get_upper_bound(),e.controllable))
             
     #   f.write("}")
       # f.close()
        # self.mip_solver()
        
    def estimate_default(self):
        if self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
            return
        self.DEFAULT = 100
        for e in self.network.temporal_constraints.values():
            if e.get_upper_bound() > 1000:
                continue
        
            if e.get_upper_bound() *1.2 > self.DEFAULT:
                self.DEFAULT = e.get_upper_bound()*1.2
        #print(self.DEFAULT)
                
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
        
        if self.objective_type == ObjectiveType.MIN_COST:
            self.rl = {}
            self.ru = {}
            self.tl = {}
            self.tu = {}
        for e in self.network.temporal_constraints.values():
            #if e.activated:
                self.l[(e.fro, e.to)] = LinExpr()
                self.u[(e.fro, e.to)] = LinExpr()


        
    def calc_distance(self):
        self.dis = {}
        # for RCPSP Problem, the number of nodes are limited        
        for node_a in range(1, self.num_nodes + 1):
            for node_b in range(node_a + 1, self.num_nodes + 1):
                if (node_a, node_b) not in self.dis:
                    self.dis[(node_a, node_b)] = self.dis[(node_b, node_a)] = (-self.DEFAULT, self.DEFAULT)
                    
        #return 
        for e in self.network.temporal_constraints.values():
            if e.controllable:
                tmp_lb = -self.DEFAULT
                tmp_ub = self.DEFAULT
                if tmp_lb < e.get_lower_bound():
                    tmp_lb = e.get_lower_bound()
                if tmp_ub > e.get_upper_bound():
                    tmp_ub = e.get_upper_bound()
                if self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
                    self.dis[(e.fro, e.to)] = (tmp_lb, tmp_ub)
                    self.dis[(e.to, e.fro)] = (-tmp_ub, -tmp_lb)
                else:
                    if e.relaxable_lb:
                        if tmp_lb > 0:
                            tmp_lb = 0
                        else:
                            tmp_lb = -self.DEFAULT
                    if e.relaxable_ub:
                        tmp_ub = self.DEFAULT
                    self.dis[(e.fro, e.to)] = (tmp_lb, tmp_ub)
                    self.dis[(e.to, e.fro)] = (-tmp_ub, -tmp_lb)
            else:
                if self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
                    self.dis[(e.fro, e.to)] = (e.get_lower_bound(), self.DEFAULT)
                else:
                  #  continue
                    self.dis[(e.fro, e.to)] = (e.get_lower_bound(), e.get_upper_bound())
                    #self.dis[(e.to, e.fro)] = (-e.get_upper_bound(), -e.get_lower_bound())
        
      
        #return  
        for node_k in range(1, self.num_nodes + 1):
            for node_i in range(1, self.num_nodes + 1):
                for node_j in range(1, self.num_nodes + 1):
                    if node_i != node_j and node_i != node_k and node_j != node_k:
                        #print(self.dis[(node_i, node_k)] )
                       # print(self.dis[(node_k, node_j)])
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
        for node_id in range(1, self.num_nodes + 1):
            self.v_set[node_id] = 0
        self.v_set[e.fro] = 3
        self.v_set[e.to] = 3
        #return 
        self.b_change = False
        
        for node_id in range(1, self.num_nodes + 1):
            if node_id != e.fro and node_id != e.to:
                B = node_id
                if self.dis[(e.fro, B)][1] <= self.dis[(e.fro, e.to)][0]:
                    self.v_set[node_id] = -2 #pre-set
                elif self.dis[(e.fro, B)][0] >= self.dis[(e.fro, e.to)][0]:
                    self.v_set[node_id] = 1 #post-set
                else:
                    self.v_set[node_id] = -1 #other
        
        #pre-migrations
        for e1 in self.network.temporal_constraints.values():
            if e1 == e or e1.controllable:
                continue
            E = e1.fro
            F = e1.to
            if self.v_set[F] == -1 and self.dis[(e.fro, F)][1] >= 0:
                self.v_set[F] = 0
                self.v_set[E] = 0
                self.b_change = True
        self.b_change = True
        while self.b_change == True:
            self.b_change = False
            for e1 in self.network.temporal_constraints.values():
                if e1 == e or e1.controllable:
                    continue
                E = e1.fro
                F = e1.to
                if self.v_set[F] != 1:
                    continue
                if self.dis[(e.to, F)][0] < 0:
                    self.v_set[F] = 0
                    self.v_set[E] = 0
                    self.b_change = True
                    continue
                if self.v_set[F] == 0 and self.v_set[E] == 0:
                    continue
                for e2 in self.network.temporal_constraints.values():
                    if e == e2 or e1 == e2 or e2.controllable:
                        continue
                    if self.v_set[e2.fro] != 0 or self.dis[(e2.fro, F)][0] <0:
                        self.v_set[F] = 0
                        self.v_set[E] = 0
                        self.b_change = True
                        break
                    
            
                 
        
        # find the guard nodes
        self.b_v = {}
        for node_id in range(1, self.num_nodes + 1):
            self.b_v[node_id] = False
        self.b_v[e.fro] = True
        self.guardDFS(e.to)
        
    def precede_reduce(self, e):
        for node_id in range(1, self.num_nodes + 1):
            self.v_set[node_id] = 0
        #self.b_change = False
        self.v_set[e.fro] = 2
        self.v_set[e.to] = 2
        #return
        self.b_v = {}
        for node_id in range(1, self.num_nodes + 1):
            if node_id != e.fro and node_id != e.to:
                if self.dis[(e.to, node_id)][0] >= 0: 
                    self.v_set[node_id] = 1 #post-set
                elif self.dis[(e.to ,node_id)][1] < 0:
                    self.v_set[node_id] = -1 #pre-set
                else:
                    self.v_set[node_id] = 0 #other
        
        for node_id in range(1, self.num_nodes + 1):
            self.b_v[node_id] = False
        self.b_v[e.fro] = True
        self.guardDFS(e.to)
        
        
    def guardDFS(self, x):
        
        if self.b_v[x]:
            return
        self.b_v[x] = True
        
        if self.v_set[x] == -1:
            self.v_set[x] = 0
            self.b_change = True
            return 
        
        for node_id in range(1, self.num_nodes + 1):
            if not self.b_v[node_id] and ((x, node_id) in self.encoded_node_pairs or (node_id,x) in self.encoded_node_pairs)and self.v_set[node_id] != 0:
                self.guardDFS(node_id)
            
            
    def add_vars(self, m):
        
        # add the extra variable to represent minimum delay
        if self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
            self.Z = m.addVar(vtype = GRB.CONTINUOUS, lb = 0, name = "Z")
        else:
            self.objexp = 0;
        
        # add variables for links
        self.encoded_node_pairs = {}
        self.ctg_by_fro = {}
        self.relax_e = {}
        K = 0

        for e in self.network.temporal_constraints.values():
            
            # We only consider constraints that are active
            if e.activated:
                if e.fro == 0 or e.to == 0:
                    raise Exception("Node with id zero is not allowed (see documentation for check function.)")
                #print('a', e.fro, e.to, e.controllable, e.relaxable_lb, e.relaxable_ub, e.get_lower_bound(), e.get_upper_bound())
                if e.controllable:
                    
                    # Make sure no two edges share the same from and to nodes
                    if (e.fro, e.to) not in self.encoded_node_pairs:
                        # add_controllable(e.fro,e.to,e.get_lower_bound(),e.get_upper_bound(),e.id)
                        if self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
                            self.l[(e.fro, e.to)] += m.addVar(lb=self.dis[(e.fro, e.to)][0], ub=self.dis[(e.fro, e.to)][1], vtype=GRB.CONTINUOUS, name="l_%s_%s" % (e.fro - 1, e.to - 1))
                            self.u[(e.fro, e.to)] += m.addVar(lb=self.dis[(e.fro, e.to)][0], ub=self.dis[(e.fro, e.to)][1], vtype=GRB.CONTINUOUS, name="u_%s_%s" % (e.fro - 1, e.to - 1))
                    
                        else:
                            # the relaxable links are [L-l, U+u]
                            #print("vtl", e.fro, e.to)
                            self.tl[(e.fro, e.to)] = m.addVar(ub = self.DEFAULT,vtype = GRB.CONTINUOUS, name = "vlt_%s_%s"%(e.fro - 1, e.to - 1))
                            self.tu[(e.fro, e.to)] = m.addVar(ub = self.DEFAULT,vtype = GRB.CONTINUOUS, name = "vut_%s_%s"%(e.fro - 1, e.to - 1))
                            if e.relaxable_lb == True:
                                #print(e.fro)
                                #print(e.fro, e.to, "v")
                                self.rl[(e.fro, e.to)] = m.addVar(ub = self.DEFAULT,vtype = GRB.CONTINUOUS, name = "vlr_%s_%s"%(e.fro- 1, e.to - 1))
                                self.relax_e["vlr_%s_%s"%(e.fro- 1, e.to - 1)] = e
                            if e.relaxable_ub == True:
                                self.ru[(e.fro, e.to)] = m.addVar(ub = self.DEFAULT,vtype = GRB.CONTINUOUS, name = "vur_%s_%s" % (e.fro - 1, e.to - 1))
                                self.relax_e["vur_%s_%s"%(e.fro- 1, e.to - 1)] = e
                        self.encoded_node_pairs[(e.fro, e.to)] = True
                    else:
                        print("error")
                else:
                    K += 1
#                    print(e.fro, e.to, e.name, e.get_lower_bound(), e.get_upper_bound())
                    if e.relaxable_lb == True:
                        self.l[(e.fro, e.to)] += m.addVar(lb=e.get_lower_bound(), ub=e.get_upper_bound(), vtype=GRB.CONTINUOUS, name="cl_%s_%s" % (e.fro - 1, e.to - 1))  # name=e.name + "l")
                        self.relax_e["cl_%s_%s" % (e.fro - 1, e.to - 1)] = e
                    else:
                        self.l[(e.fro, e.to)] += e.get_lower_bound()
                    if e.relaxable_ub == True:
                        self.u[(e.fro, e.to)] += m.addVar(lb=e.get_lower_bound(), ub=e.get_upper_bound(), vtype=GRB.CONTINUOUS, name="cu_%s_%s" % (e.fro - 1, e.to - 1))  # name=e.name + "u")
                        self.relax_e["cu_%s_%s" % (e.fro - 1, e.to - 1)] = e
                    else:
                        self.u[(e.fro, e.to)] += m.addVar(lb=e.get_upper_bound(), ub=e.get_upper_bound(), vtype=GRB.CONTINUOUS, name="cu_%s_%s" % (e.fro - 1, e.to - 1))  # name=e.name + "u")
                        self.relax_e["cu_%s_%s" % (e.fro - 1, e.to - 1)] = e
                    self.encoded_node_pairs[(e.fro, e.to)] = True
                    self.ctg_by_fro[e.fro] = e
     
    
    def add_additional_vars(self, m): 
        self.precede_pair = {}
        self.wait_pair = {}      # keep a record of added wait variables
  
        for e in self.network.temporal_constraints.values():
            
            # We only consider constraints that are active
            if e.activated:
                if e.fro == 0 or e.to == 0:
                    raise Exception("Node with id zero is not allowed (see documentation for check function.)")
                
                # add wait and precede constraints according to contingent links
                if e.controllable == False:  
               
                    b_update = True     # flag of update
                    # add links repeatedly until no update
                    while b_update == True:
                        b_update = False     
                        # find necessary nodes to add links and mark the nodes by v_set
                        self.v_set = {}
                        self.wait_reduce(e)
#                         for node_id in range(1, self.num_nodes + 1):
#                             self.v_set[node_id] = 0
#                         self.v_set[e.fro] = 1
#                         self.v_set[e.to] = 1
                        
                        # add variables and constraints for the added links
                        for node_id in range(1, self.num_nodes + 1):
                            if node_id != e.fro and node_id != e.to:
                                # wait constraints are added within triangle (e.fro, e.to, node_id)
                                if self.v_set[node_id] == 0:
                                    
                                    # add link (e.fro, node_id)
                                    if (e.fro, node_id) not in self.encoded_node_pairs and (node_id, e.fro) not in self.encoded_node_pairs:
                                        self.add_var_rqm(m, e.fro, node_id)
                                        b_update = True
                                        
                                    # add link (node_id, e.to)
                                    if (node_id, e.to) not in self.encoded_node_pairs and (e.to, node_id) not in self.encoded_node_pairs:
                                        b_update = True
                                        self.add_var_rqm(m, node_id, e.to)
                                    
                                    # add wait (e.fro, node_id)                                 
                                    if (e.fro, node_id) not in self.wait_pair:
                                        # add wait variable
                                        if self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
                                            self.w[(e.fro, node_id)] = m.addVar(lb=self.dis[(e.fro, node_id)][0], vtype=GRB.CONTINUOUS, name="w_%s_%s" % (e.fro - 1, node_id - 1))
                                        else:
                                            self.w[(e.fro, node_id)] = m.addVar(lb=-self.DEFAULT ,ub= self.DEFAULT, vtype=GRB.CONTINUOUS, name="w_%s_%s" % (e.fro - 1, node_id - 1))

                                        # add binary variable wab - lac >= 0, then b = 1
                                        self.b[(e.fro, node_id)] = m.addVar(vtype=GRB.BINARY, name="x-lc_%s_%s_%s" % (e.fro - 1, node_id - 1, e.to - 1))
                                        self.wait_pair[(e.fro, node_id)] = True
                        
                        self.precede_reduce(e)
                       # if b_update == False:
                       #     b_update = self.b_change
                        
                        for node_id in range(1, self.num_nodes + 1):
                            if node_id != e.fro and node_id != e.to:
                                if self.v_set[node_id] == 0:
                                    
                                    if (e.fro, node_id) not in self.encoded_node_pairs and (node_id, e.fro) not in self.encoded_node_pairs:
                                        self.add_var_rqm(m, e.fro, node_id)
                                        b_update = True
                                    
                                    if (node_id, e.to) not in self.encoded_node_pairs and (e.to, node_id) not in self.encoded_node_pairs:
                                        self.add_var_rqm(m, node_id, e.to)
                                        b_update = True
                                    
                                    if (e.fro, node_id) not in self.precede_pair:
                                        self.precede_pair[(e.fro, node_id)] = True   
                                        # add binary variable lbc >= 0, x = 1
                                        self.x[(node_id, e.to)] = m.addVar(vtype=GRB.BINARY, name="b_%s_%s_%s" % (e.fro - 1, node_id - 1, e.to - 1))
                                
                                        
                                
    def add_constrs(self, m):  
        if self.objective_type == ObjectiveType.MIN_COST:
            for e in self.network.temporal_constraints.values():
                if e.fro == 0 or e.to == 0:
                    raise Exception("Node with 0")
                if not e.activated:
                    continue
                if e.controllable:
                    #print(e.fro, e.to, e.get_lower_bound(),e.get_upper_bound())
                    self.l[(e.fro, e.to)] = e.get_lower_bound() + self.tl[(e.fro, e.to)]
                    self.u[(e.fro, e.to)] = e.get_upper_bound() - self.tu[(e.fro, e.to)]
                    if e.relaxable_lb == True:
                        #print(e.fro, e.to, e.name)
                        self.l[(e.fro, e.to)] -= self.rl[(e.fro, e.to)]
                    if e.relaxable_ub == True:
                        self.u[(e.fro, e.to)] += self.ru[(e.fro, e.to)]
                else:
                    if e.relaxable_lb or e.relaxable_ub:
                        m.addConstr(self.l[(e.fro, e.to)] <= self.u[(e.fro, e.to)])
        
        added_pairs ={}
        for (node_a, node_b) in self.encoded_node_pairs:
            
            # add the opposite expressions of links
            self.l[(node_b, node_a)] = -self.u[(node_a, node_b)]
            self.u[(node_b, node_a)] = -self.l[(node_a, node_b)]
            added_pairs[(node_b, node_a)] = True 
            
            # l <= u
           # print(node_a, node_b, self.l[(node_a, node_b)], self.u[(node_a, node_b)])
           # if self.l[(node_a, node_b)].getVar(1) is not None or self.u[(node_a, node_b)].getVar(1) is not None:
            #if self.l[(node_a, node_b)].size():
            m.addConstr(self.l[(node_a, node_b)] -self.u[(node_a, node_b)] <= 0, "Ub_%s_%s" % (node_a - 1, node_b - 1))
       
        for (node_a, node_b) in added_pairs:
            self.encoded_node_pairs[(node_a, node_b)] = True
        
        for e in self.network.temporal_constraints.values():
            if e.activated:
                if not e.controllable:
                    # add z <= u - l
                    if self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
                        m.addConstr(self.Z <= self.u[(e.fro, e.to)] - self.l[(e.fro, e.to)], "ZC%s" % (e.fro / 2))
                    else:
                        # relax a ctg means tightening the bounds
                        if e.relaxable_lb:
                            #print(self.l[(e.fro, e.to)] )
                            self.objexp += (self.rl[(e.fro, e.to)] )*e.relax_cost_lb
                            #self.objexp += (self.l[(e.fro, e.to)] - self.dis[(e.fro, e.to)][0])*e.relax_cost_lb
                        if e.relaxable_ub:
                            self.objexp += (self.ru[(e.fro, e.to)])*e.relax_cost_ub

                            # self.objexp += -(self.u[(e.fro, e.to)] - self.dis[(e.fro, e.to)][1])*e.relax_cost_ub
                else:
                    # relax a rqm means extending the bounds
                    m.addConstr(self.l[e.fro,e.to] <= self.u[(e.fro,e.to)])
                    if e.relaxable_lb:
                        # print(self.l[(e.fro, e.to)])
                        m.addConstr(self.l[(e.fro, e.to)] >= 0)
                        self.objexp += (self.rl[(e.fro, e.to)] )*e.relax_cost_lb
                        #self.objexp += -(self.l[(e.fro, e.to)] - self.dis[(e.fro, e.to)][0])*e.relax_cost_lb
                    if e.relaxable_ub:
                        #print(self.ru[(e.fro, e.to)],e.relax_cost_ub)
                        self.objexp += (self.ru[(e.fro, e.to)])*(e.relax_cost_ub)
                        #self.objexp += (self.u[(e.fro, e.to)] - self.dis[(e.fro, e.to)][1])*e.relax_cost_ub

        for (node_a, node_b) in self.wait_pair:
            # l <= w <= u
            #m.addConstr(self.l[(node_a, node_b)] <= self.w[(node_a, node_b)], "wb%s_%s_l" % (node_a, node_b))
            m.addConstr(self.w[(node_a, node_b)] <= self.u[(node_a, node_b)], "wb%s_%s_u" % (node_a, node_b))                                
            
            e = self.ctg_by_fro[node_a]
            # triangular wait
            m.addConstr(self.w[(node_a, node_b)] >= self.u[(e.fro, e.to)] - self.u[(node_b, e.to)], "TriW_%s_%s_%s" % (node_a, node_b, e.to))
        
            # add wait bounds
            # wab - lac + (b-1) * L>=0
            tmp_lb = self.dis[(node_a, node_b)][0]-self.dis[(e.fro, e.to)][1]
            if self.objective_type == ObjectiveType.MIN_COST:
                tmp_lb = -self.DEFAULT*3
            m.addConstr(self.w[(node_a, node_b)] - self.l[(e.fro, e.to)] + (self.b[(node_a, node_b)] - 1) * (tmp_lb) >= 0, "WaitB_%s_%s" % (node_a, node_b))
            # wab - lac - b * U <=0
            tmp_ub = self.dis[(node_a, node_b)][1] - self.dis[(e.fro, e.to)][0]
            if self.objective_type == ObjectiveType.MIN_COST:
                tmp_ub = self.DEFAULT*3
            m.addConstr(self.w[(node_a, node_b)] - self.l[(e.fro, e.to)] - self.b[(node_a, node_b)] * (tmp_ub) <= 0, "WaitB2_%s_%s" % (node_a, node_b))
            # lab - lac + (b-1) * L >=0
            tmp_lb = self.dis[(node_a, node_b)][0] - self.dis[(e.fro, e.to)][1]
            if self.objective_type == ObjectiveType.MIN_COST:
                tmp_lb = -self.DEFAULT*3
            m.addConstr(self.l[(node_a, node_b)] - self.l[(e.fro, e.to)] + (self.b[(node_a, node_b)] - 1) * (tmp_lb) >= 0, "WaitB3_%s_%s" % (node_a, node_b))
            # lab - wab - b * L >= 0
            tmp_lb = self.dis[(node_a, node_b)][0] - self.dis[(node_a, node_b)][1]
            if self.objective_type == ObjectiveType.MIN_COST:
                tmp_lb = -self.DEFAULT*3
            m.addConstr(self.l[(node_a, node_b)] - self.w[(node_a, node_b)] - self.b[(node_a, node_b)] * (tmp_lb) >= 0, "WaitB4_%s_%s" % (node_a, node_b))
        
            # add regression waits
            for e1 in self.network.temporal_constraints.values():
                if e1.to == node_b and (node_a, e1.fro) in self.wait_pair:
                    if e1.controllable == False:
                        # if wab >= lac, wad >= wab - ldb
                        m.addConstr(self.w[(node_a, e1.fro)] - self.w[(node_a, node_b)] + self.l[(e1.fro, e1.to)] - (1 - self.b[(node_a, node_b)]) * (-self.DEFAULT*3) >= 0 , "RegW_C%s_%s_%s" % (node_a, e1.fro, node_b))
                    else:
                        m.addConstr(self.w[(node_a, e1.fro)] - self.w[(node_a, node_b)] + self.u[(e1.fro, e1.to)] - (1 - self.b[(node_a, node_b)]) * (-self.DEFAULT*3) >= 0 , "RegW_C%s_%s_%s" % (node_a, e1.fro,node_b))
          
                  #  break
        

        for (A, B) in self.precede_pair:
            # precede constraints
            C = self.ctg_by_fro[A].to
            e = self.ctg_by_fro[A]
            
            if self.dis[(B, C)][0] > 0 and self.dis[(B,C)][1] > 0:
                # lab = uac - ubc
                m.addConstr(self.l[(A, B)] - (self.u[(A, C)] - self.u[(B, C)]) >= 0, "pl%s_%s" % (A, B))
                # uab = lac - lbc
                m.addConstr(self.u[(A, B)] - (self.l[(A, C)] - self.l[(B, C)]) <= 0, "pu%s_%s" % (A, B))
        
            elif self.dis[(B, C)][1] >0:
           # if self.dis[(B, C)][1] > 0 :
                t_lb = -self.DEFAULT
                t_ub = self.DEFAULT
                if self.objective_type != ObjectiveType.MIN_COST:
                    t_lb = self.dis[(B,C)][0]
                    t_ub = self.dis[(B,C)][1]
                # x (lab - uac + ubc) = 0
                m.addConstr(self.x[(B, C)] * (self.l[(A, B)] - self.u[(e.fro, e.to)] + self.u[(B, e.to)]) >= 0, "pbl%s_%s" % (A, B))
                # x (uab - lac + lbc) = 0
                m.addConstr(self.x[(B, C)] * (self.u[(A, B)] - self.l[(e.fro, e.to)] + self.l[(B, e.to)]) <= 0, "pbu%s_%s" % (A, B))
                # lbc - xU <= 0
                m.addConstr(self.l[(B, C)] - self.x[(B, C)] * (t_ub+1) <= 0, "pbxu%s_%s" % (A, B))
                # lbc + (x-1)(L-1) >= 0
                m.addConstr(self.l[(B, C)] + (self.x[(B, C)] - 1) * (t_lb-1) >= 1e-6, "pbxl%s_%s" % (A , B))
        
                
                
                            
    def add_var_rqm(self, m, fro, to):
        # add variables for a requirement link
        
        # add l[fro, to] and u[fro, to]
        self.l[(fro, to)] = LinExpr()
        self.u[(fro, to)] = LinExpr()
        self.l[(fro, to)] += m.addVar(lb=self.dis[(fro, to)][0], ub=self.dis[(fro, to)][1], vtype=GRB.CONTINUOUS, name="l_%s_%s" % (fro - 1, to - 1))
        self.u[(fro, to)] += m.addVar(lb=self.dis[(fro, to)][0], ub=self.dis[(fro, to)][1], vtype=GRB.CONTINUOUS, name="u_%s_%s" % (fro - 1, to - 1))
        self.encoded_node_pairs[(fro, to)] = True
#         m.update()
#         # the opposite direction
#         self.l[(to, fro)] = -self.u[(fro, to)]
#         self.u[(to, fro)] = -self.l[(fro, to)]
#         self.encoded_node_pairs[(to, fro)] = True                                                                                            
                        
    def add_spc(self, m):
        
        cnt = {}
        b_del = {}
        
        # calc 
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
            cnt[node_a] = 1.0 * cnt2 / (cnt1+1)                       
                        
        for round_id in range(1, self.num_nodes+1):
            next_node = 0
            for node_id in range(1, self.num_nodes + 1):
                if b_del[node_id] and (next_node == 0 or cnt[next_node] < cnt[node_id]):
                    next_node = node_id                                 
            
            # print(round_id, next_node)
            adjacent = []
            for node_id in range(1, self.num_nodes + 1):
                if b_del[node_id] == False:
                    continue
                #if node_id != next_node:
                if (node_id, next_node) in self.encoded_node_pairs or (next_node,node_id) in self.encoded_node_pairs: 
                    adjacent.append(node_id)
            
            b_del[next_node] = False
            
            A = next_node
            for B in adjacent:
                for C in adjacent:
                    if B != C:
                        # add shortest path constraints
                        if (B, C) not in self.encoded_node_pairs :
                            #continue
                            #print("add edge")
                            self.add_var_rqm(m, B, C)
                            m.update()
                            self.l[(C, B)] = -self.u[(B, C)]
                            self.u[(C, B)] = -self.l[(B, C)]
                            self.encoded_node_pairs[(C, B)] = True 
            
            # l <= u
           # print(node_a, node_b, self.l[(node_a, node_b)], self.u[(node_a, node_b)])
           # if self.l[(node_a, node_b)].getVar(1) is not None or self.u[(node_a, node_b)].getVar(1) is not None:
            #if self.l[(node_a, node_b)].size():
                            m.addConstr(self.l[(B, C)] -self.u[(B, C)] <= 0, "Ub_%s_%s" % (B - 1, C - 1))
      
                        
                        # lac <= lab + ubc
                        m.addConstr(self.l[(A, C)] - self.u[(A, B)] - self.l[(B, C)] <= 0, "SPC_%s_%s_%s_1" % (A - 1, B - 1, C - 1))
                        # lac <= uab + lac
                        m.addConstr(self.l[(A, C)] - self.l[(A, B)] - self.u[(B, C)] <= 0, "SPC_%s_%s_%s_2" % (A - 1, B - 1, C - 1))
                        # lab + ubc <= uac
                        m.addConstr(self.u[(A, C)] - self.l[(A, B)] - self.u[(B, C)] >= 0, "SPC_%s_%s_%s_3" % (A - 1, B - 1, C - 1))
                        # uab + lbc <= uac
                        m.addConstr(self.u[(A, C)] - self.u[(A, B)] - self.l[(B, C)] >= 0, "SPC_%s_%s_%s_4" % (A - 1, B - 1, C - 1))
                        # uac <= uab + ubc
                        m.addConstr(self.u[(A, C)] - self.u[(A, B)] - self.u[(B, C)] <= 0, "SPC_%s_%s_%s_5" % (A - 1, B - 1, C - 1))
                        # lac >= lab + lbc 
                        m.addConstr(self.l[(A, C)] - self.l[(A, B)] - self.l[(B, C)] >= 0, "SPC_%s_%s_%s_6" % (A - 1, B - 1, C - 1))
                        
    def get_solution(self, m):                    
        solution = Candidate()
        
      #  f = open('sol.txt', 'w')
        
        for var_a in m.getVars():
            vname = var_a.getAttr(GRB.Attr.VarName)
            if self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
                if vname.find("cl") == -1 and vname.find("cu") == -1:
                    continue
                
                #f.write('%s    %s\n' % (var_a.getAttr(GRB.Attr.VarName), var_a.getAttr(GRB.Attr.X)))
                
                # if vname.find("l") != -1:
                #   print(var_a.getAttr(GRB.Attr.VarName), var_a.getAttr(GRB.Attr.X))
                e = self.relax_e[vname]
    
                new_relaxation = TemporalRelaxation(e)
                if vname.find("cl") != -1:
                    new_relaxation.relaxed_lb = var_a.getAttr("X")
                    if new_relaxation.relaxed_lb != e.get_lower_bound():
                        solution.add_temporal_relaxation(new_relaxation)                            
                else :
                    new_relaxation.relaxed_ub = var_a.getAttr("X")
                    if new_relaxation.relaxed_ub != e.get_upper_bound():
                        solution.add_temporal_relaxation(new_relaxation)   
            elif self.objective_type == ObjectiveType.MIN_COST:
                if vname.find("vlr") == -1 and vname.find("vur") == -1:
                    continue;
                e = self.relax_e[vname]
                #print(vname,e.fro, e.to)
                new_relaxation = TemporalRelaxation(e)
                if vname.find("vlr") != -1:
                    new_relaxation.relaxed_lb = self.l[(e.fro,e.to)].getValue()
                else:
                    new_relaxation.relaxed_ub = self.u[(e.fro, e.to)].getValue()
                if var_a.getAttr("X") > 0:
                    solution.add_temporal_relaxation(new_relaxation)
#        for e in self.network.temporal_constraints.values():
#            if e.activated:
#                print(e.fro, e.to, self.l[(e.fro, e.to)].getValue(), self.u[(e.fro, e.to)].getValue())
                                     
                    
        solution.utility = round(m.getObjective().getValue(), 6)
        if solution.utility > 1000 and self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
            solution.utility = 1000
        
#         for node_a in range(1, self.num_nodes+1):
#             for node_b in range(1, self.num_nodes+1):
#                 if node_a != node_b:
#                     f.write("%s->%s [%s, %s]\n"%(node_a,node_b,self.l[(node_a,node_b)].getValue(), self.u[(node_a,node_b)].getValue() ))
#        # if solution.utility > 100:
        #    solution.utility = 100
      #  f.close()
        
        #print a dot file
     #   f = open('sol.dot', 'w')
      #  f.write('digraph G {\n nodesep = .45; \n size = 30;\n label="CCTP";\n')
#          
#         for e in self.network.temporal_constraints.values():
#             if e.activated:
#                 f.write('"%s"->"%s"'%(e.fro, e.to))
#                 tlb = self.l[(e.fro, e.to)].getValue()
#                 tub = self.u[(e.fro, e.to)].getValue() 
#                 f.write('[ label = "[%s,%s]'%(tlb, tub))
#                 if not e.controllable:
#                     f.write(' type=dashed')
#                 f.write('"];\n')           
#                  #%d"];'%(e.fro, e.to,e.get_lower_bound(),e.get_upper_bound(),e.controllable))
             
      #  f.write("}")
      #  f.close()
        return solution     
        
    def mip_solver(self):
        
        try:
            
            # create a new model
            m = Model("mip_encode")
            m.params.outputflag = 0
            #m.params.feasibilitytol = 1e-9
            #m.params.intfeastol = 1e-9
            # add variables
            self.add_vars(m)
            self.add_additional_vars(m)
            
            # integrate new variables
            m.update()
            # print("add constr")

            # add constraints
            self.add_constrs(m)
            self.add_spc(m)
            if self.objective_type == ObjectiveType.MAX_FLEX_UNCERTAINTY:
                m.setObjective(self.Z + 0.0, GRB.MAXIMIZE)
            else:
                m.setObjective(self.objexp, GRB.MINIMIZE)
            m.update()
            m.write("1.lp")
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
            print (e.errno)
        solution = Candidate()
        solution.utility = -1;
        return solution


