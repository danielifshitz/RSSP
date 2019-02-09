from cplex_equations import Equations
from tree import Tree

class B_and_B():

    def __init__(self, obj, ub, lb, ctype, colnames, rhs, rownames, sense, rows, cols, vals, x_names, UB=None, use_SP=True, solution_type="minimize"):
        self.best_equation = None
        self.solution_type = solution_type
        Equations.init_global_data(obj, ub, lb, ctype, colnames, rownames, sense, len(x_names))
        self.tree = Tree()
        if UB:
            self.UB = UB
        else:
            if solution_type == "minimize":
                self.UB = float("inf")
            elif solution_type == "maximize":
                self.UB = -float("inf")
        if use_SP:
            self.__create_SPs(1, rhs, rows, cols, vals, x_names)
        else:
            equation = Equations(rhs, rows, cols, vals, x_names, {})
            self.__init_equation(None, equation, "problem.lp")


    def __create_SPs(self, op, rhs, rows, cols, vals, x_names, needed_x=[]):
        mode = 1
        sub = [s for s in x_names if "X" + str(op)+ "," +str(mode) in s]
        if not sub:
            return self.__to_delete({elem : index for index, elem in enumerate(x_names) if elem not in needed_x}, cols, rows, vals, rhs, x_names)
        while sub:
            needed_x_copy = needed_x[:]
            needed_x_copy += sub
            self.__create_SPs(op + 1, rhs, rows, cols, vals, x_names, needed_x_copy)
            mode += 1
            sub = [s for s in x_names if "X" + str(op)+ "," +str(mode) in s]
            


    def __to_delete(self, choices, cols, rows, vals, rhs, all_x):
        cols_copy = cols[:]
        rows_copy = rows[:]
        vals_copy = vals[:]
        index = 0
        while index < len(cols_copy):
            if cols_copy[index] in choices.values():
                cols_copy.pop(index)
                rows_copy.pop(index)
                vals_copy.pop(index)
            else:
                index += 1
        choices = {choice: 0 for choice in choices}
        not_init_x = [x for x in all_x if x not in choices.keys()]
        equation = Equations(rhs, rows, cols, vals, not_init_x, choices)
        self.__init_equation(None, equation)


    def __update_UB(self, equation):
        """
        check the equation and if their solution better then the UB, update UB 
            and save the equation equatiosn: Equation, the equation of a node
        return: None
        """
        solution = equation.solution
        if solution and self.solution_type == "minimize" and solution < self.UB:
            self.UB = solution
            self.best_equation = equation
        elif solution and self.solution_type == "maximize" and solution > self.UB:
            self.UB = solution
            self.best_equation = equation


    def __try_bound(self):
        """
        take the next node in the queue, if its solution worth then the UB drop this node
            repeat until node solution better then the UB or until the queue is empty
        return: Node if fuond better solution then UB or None if the queue is empty
        """
        next_node = self.tree.get_queue_head()
        while next_node: # while the queue not empty
            if self.solution_type == "minimize" and next_node.get_value() > self.UB:
                next_node = self.tree.get_queue_head() # take another node from the queue
            elif self.solution_type == "maximize" and next_node.get_value() < self.UB:
                next_node = self.tree.get_queue_head() # take another node from the queue
            else:
                return next_node
        return None


    def __init_equation(self, node, equation, file_name=None):
        """
        create new node from the equation and add it to tree queue
        node: Node, father node
        equation: Equation, cplex data
        file_name: string, where save the cplex solution
        return: None
        """
        solution = equation.solve_milp(file_name)
        if solution and equation.integer_solution:
            self.__update_UB(equation)
        else:
            self.tree.add_node(node, equation)
    
    
    def create_node(self, node, col_dict):
        """
        create new equation and add it to the B&B
        node: Node, father node
        col_dict: dict, a dict of parameters name and the selected value for them
        return: None
        """
        eq = node.equation
        equation = eq.create_son_equations(col_dict)
        self.__init_equation(node, equation)


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
                col_dict = {next_node.equation.cols_to_remove[0] : 1}
                self.create_node(next_node, col_dict)
            next_node = self.__try_bound()

        solution_data = "created nodes = {}, max depth = {}, max queue size = {}".format(self.tree.num_of_nodes,
            self.tree.max_depth, self.tree.max_queue_size)
        try:
            return self.best_equation.print_cplex_solution(), solution_data
        except:
            print("cann't find integer solution")
            return None