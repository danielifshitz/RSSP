from cplex_equations import Equations
from tree import Tree

class B_and_B():

    def __init__(self, obj, ub, lb, ctype, colnames, rhs, rownames, sense, rows, cols, vals, x_names, UB=float("inf"), use_SP=True):
        self.best_equation = None
        self.number_of_best_solutions = 0
        Equations.init_global_data(obj, ub, lb, ctype, colnames, rownames, sense, len(x_names))
        self.tree = Tree(queue_limit=10000)
        self.UB = UB
        if use_SP:
            self.__create_SPs(1, rhs, rows, cols, vals, x_names)
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
        check the equation and if their solution better then the UB, update UB 
            and save the equation equatiosn: Equation, the equation of a node
        return: None
        """
        solution = equation.solution
        if solution and solution < self.UB:
            self.UB = solution
            self.best_equation = equation
            self.number_of_best_solutions = 1
        elif solution and solution == self.UB:
            self.number_of_best_solutions += 1


    def __try_bound(self):
        """
        take the next node in the queue, if its solution worth then the UB drop this node
            repeat until node solution better then the UB or until the queue is empty
        return: Node if fuond better solution then UB or None if the queue is empty
        """
        next_node = self.tree.get_queue_head()
        while next_node: # while the queue not empty
            if next_node.get_solution() > self.UB:
                next_node = self.tree.get_queue_head() # take another node from the queue
            else:
                return next_node
        return None


    def __init_equation(self, equation, depth=0, file_name=None):
        """
        create new node from the equation and add it to tree queue
        depth: int, next node depth
        equation: Equation, cplex data
        file_name: string, where save the cplex solution
        return: None
        """
        solution = equation.solve_milp(file_name)
        if solution and equation.integer_solution:
            self.__update_UB(equation)
        elif solution:
            self.tree.add_node(equation, depth)
    
    
    def create_node(self, node, col_dict):
        """
        create new equation and add it to the B&B
        node: Node, father node
        col_dict: dict, a dict of parameters name and the selected value for them
        return: None
        """
        eq = node.equation
        equation = Equations(eq.cols[:], eq.rows[:], eq.vals[:],
            eq.rhs[:], eq.cols_to_remove[:], eq.choices.copy(), col_dict)
        self.__init_equation(equation, node.depth + 1)


    def set_x_to_one(self, node):
        choices = {}
        x_one = node.equation.cols_to_remove[0]
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
        return choices


    def solve_algorithem(self):
        """
        run the branch and bound algorithm to find the best solution for the equation.
        return: dict, string: dict is the parameters name and its value 
            and the string is the created nodes, max depth and max queue size
        """
        next_node = self.tree.get_queue_head()
        while next_node:
            if next_node.equation.cols_to_remove:
                col_dict = {next_node.equation.cols_to_remove[0] : 0}
                self.create_node(next_node, col_dict)
                col_dict = self.set_x_to_one(next_node)
                self.create_node(next_node, col_dict)
            next_node = self.__try_bound()

        solution_data = "created nodes = {}, max depth = {}, max queue size = {}".format(self.tree.num_of_nodes,
            self.tree.max_depth, self.tree.max_queue_size)
        try:
            print("number of best solutions =", self.number_of_best_solutions)
            return self.best_equation.cplex_solution(), solution_data
        except:
            print("cann't find integer solution")
            return None