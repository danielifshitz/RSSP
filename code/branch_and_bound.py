from cplex_equations import Equations
from tree import Tree
from cplex import infinity
from concurrent import futures
from threading import Lock

class B_and_B():

    def __init__(self, obj, ub, lb, ctype, colnames, rhs, rownames, sense, rows, cols, vals, x_names, LB=0, UB=float("inf"), use_SP=True):
        self.UB_lock = Lock()
        self.best_equation = None
        Equations.init_global_data(obj, ub, lb, ctype, colnames, rownames, sense, len(x_names))
        self.tree = Tree()
        self.UB = UB
        self.LB = LB
        self.use_SP = use_SP
        self.SP_len = 0
        if use_SP:
            self.__create_SPs(1, rhs, rows, cols, vals, x_names)
            self.SP_len = len(self.tree.queue)
            # print("|SPs| =", len(self.tree.queue))
            # print([round(node.get_solution(),3) for node in self.tree.queue])
        else:
            equation = Equations(cols, rows, vals, rhs, x_names, {}, {})
            self.__init_equation(equation, file_name="problem.lp")


    def __create_SPs(self, op, rhs, rows, cols, vals, x_names, needed_x=[]):
        """
        recursive function, for every SP take all operations and choice one mode.
        all SPs must be difference.
        """
        mode = 1
        sub = [s for s in x_names if "X" + str(op)+ "," +str(mode) in s]
        while sub:
            needed_x_copy = needed_x[:]
            needed_x_copy += sub
            self.__create_SPs(op + 1, rhs, rows, cols, vals, x_names, needed_x_copy)
            mode += 1
            sub = [s for s in x_names if "X" + str(op)+ "," +str(mode) in s]
        if not [s for s in x_names if "X" + str(op) in s]:
            equation = Equations(cols[:], rows[:], vals[:], rhs[:], x_names[:],{},
                {elem : 0 for elem in x_names if elem not in needed_x})
            self.__init_equation(equation)


    def __update_UB(self, equation):
        """
        check the equation solution and if it's better then the UB, update UB,
        save the equation and set the number of the solutions to one.
        if its equals to the UB increase the number of the solutions.
        use lock to check the UB to avoid conflicts.
        equatiosn: Equation, an equation with integer solution
        return: None
        """
        self.UB_lock.acquire()
        solution = equation.solution
        print("found UB that is eqauls to %10f" % solution)
        if solution and solution <= self.UB:
            self.UB = solution
            self.best_equation = equation
        self.UB_lock.release()


    def __try_bound(self):
        """
        try to take node from the queue, if its solution worth then the UB drop this node,
        repeat until node solution better or equals to the UB or until the queue is empty.
        if the queue is empty but there are threads that not finished yet, wait for them.
        return: Node if fuond better or equals solution then UB or None if the queue is empty
        """
        next_node = self.tree.get_queue_head()
        while next_node and self.LB < self.UB: # while the queue not empty
            # if the node worth then the UB, take another node
            if next_node.get_solution() > self.UB:
                next_node = self.tree.get_queue_head() # take another node from the queue
            elif next_node.get_solution() == self.UB and self.best_equation:
                next_node = self.tree.get_queue_head() # take another node from the queue
            else:
                return next_node
        # return None if the queue is empty and all the tree was bound
        return None


    def __init_equation(self, equation, depth=0, file_name=None):
        """
        create new node from the equation and add it to the queue.
        equation: Equation, cplex equation
        depth: int, next node depth
        file_name: string, where save the cplex solution, or None
        return: None
        """
        # solve LP using cplex
        solution = equation.solve_milp(file_name)
        # if the solution is integer, check the UB
        if solution and equation.integer_solution:
            self.__update_UB(equation)
        # if the solution better or equals to the UB, add it to the queue
        elif solution and solution <= self.UB:
            self.tree.add_nodes(equation, depth)
    
    
    def create_node(self, node, col_dict):
        """
        create new equation, solve it and add it to the B&B queue
        node: Node, father node
        col_dict: dict, a dict of parameters name and the selected value for them
        return: None
        """
        eq = node.equation
        equation = Equations(eq.cols[:], eq.rows[:], eq.vals[:],
            eq.rhs[:], eq.cols_to_remove[:], eq.choices.copy(), col_dict)
        self.__init_equation(equation, node.depth + 1)


    def set_x_to_one(self, node, x_one):
        """
        take all the not set Xi,m,r,l from the node and set the chosen Xi,m,r,l to
        value of one and set all blocked (by the equations) Xi,m,r,l to zero.
        all the choices will be save at a dictionary that will contain Xi,m,r,l : chosen value
        node: Node, from that node we will create new node
        x_one: string, the chosen Xi,m,r,l
        return None
        """
        choices = {}
        choices[x_one] = 1
        i, m, r, l = x_one[1:].split(",")
        # if Xi,m,r,l = 1
        for x in node.equation.cols_to_remove:
            other_i, other_m, other_r, other_l = x[1:].split(",")
            # Xj,n,t,k = 0 | j = i, n = m, t = r and k != l
            if i == other_i and m == other_m and r == other_r and l != other_l:
                choices[x] = 0
            # Xj,n,t,k = 0 | j != i, n = or != m, t = r and k = l
            elif i != other_i and r == other_r and l == other_l:
                choices[x] = 0
            # Xj,n,t,k = 0 | j = i, n != m, t = or != r and k = or != l
            elif i == other_i and m != other_m:
                choices[x] = 0
        self.create_node(node, choices)


    def zero_one_initialize(self, node):
        # create dictionary with one Xi,m,r,l equals to zero
        col_dict = {node.equation.cols_to_remove[0] : 0}
        # son with Xi,m,r,l = 0
        self.create_node(node, col_dict)
        # son with Xi,m,r,l = 1
        self.set_x_to_one(node, node.equation.cols_to_remove[0])


    def choice_resource(self, node):
        i, m, r = node.equation.cols_to_remove[0][1:-2].split(",")
        zero_choices = {}
        for x in node.equation.cols_to_remove:
            other_i, other_m, other_r = x[1:-2].split(",")
            if i == other_i and m == other_m and r == other_r:
                self.set_x_to_one(node, x)
                zero_choices[x] = 0
        if not self.use_SP:
            self.create_node(node, zero_choices)


    def solve_algorithem(self, init_resource_labels=False, disable_prints=True, cplex_auto_solution=False):
        """
        run the branch and bound algorithm to find the best solution for the equation.
        after the node where created/began to created, take node from the queue.
        when the queue is empty and the algorithm end, solve the best equation one more time
        to get all the chosen value for the Xi,m,r,l.
        return: dict, string: dict - the parameters name and chosen values,
            string - number of created nodes, max depth and max queue size
        """
        if init_resource_labels:
            initialize_x_function = self.choice_resource
        else:
            initialize_x_function = self.zero_one_initialize
        next_node = self.tree.get_queue_head()
        # run while the node not None which mean that the algorithm not end
        while next_node:
            # TODO check if this condition is necessary
            if next_node.equation.cols_to_remove:
                initialize_x_function(next_node)
            # check if we can do bound on the tree and take next node from the queue
            next_node = self.__try_bound()
        try:
            choices, nodes = self.best_equation.cplex_solution(disable_prints)
            if not cplex_auto_solution:
                nodes = self.tree.num_of_nodes
            return choices, nodes, self.tree.max_queue_size, self.SP_len, self.best_equation.solution, Equations.MIP_infeasible
        except:
            print("cann't find integer solution")
            return None, 0, 0, 0, 0, True