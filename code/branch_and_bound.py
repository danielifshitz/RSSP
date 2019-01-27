from tree import Tree
class B_and_B():

    def __init__(self, equation, UB=None, solution_type="minimize"):
        self.best_equation = None
        self.equation = equation
        self.solution_type = solution_type
        self.LB = equation.solve_milp()
        equation.prob.write("file.lp")
        input("press any key to continue 1")
        if UB:
            self.UB = UB
        else:
            if solution_type == "minimize":
                self.UB = float("inf")
            elif solution_type == "maximize":
                self.UB = -float("inf")
        if equation.is_integer_solution():
            self.__update_UB(equation)
        self.tree = Tree(equation, solution_type)
        #print("LB = ", self.LB, ", UB = ", self.UB, "\n", self.tree)
        #input("press any key to continue 2")


    def __update_UB(self, equation):
        """
        check the equation and if their solution better then the UB, update UB and save the equation
        equatiosn: Equation, the equation of a node
        return: None
        """
        solution = equation.get_solution()
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
                #print("node ", next_node.name, " with value ", next_node.get_value(), " bounded")
                next_node = self.tree.get_queue_head() # take another node from the queue
            elif self.solution_type == "maximize" and next_node.get_value() < self.UB:
                #print("node ", next_node.name, " with value ", next_node.get_value(), " bounded")
                next_node = self.tree.get_queue_head() # take another node from the queue
            else:
                return next_node
        return None
    
    
    def init_BB_equation(self, node):
        """
        
        """
        eq = node.get_equations()
        if not eq.cols_to_remove:
            return None
        equation = eq.create_sons_equations(eq.cols_to_remove[0])
        #print("\n\nequation[0]:\n", equation[0])
        #input("press any key to continue 3")
        equation[0].solve_milp()
        #input("press any key to continue 4")
        #print("\n\nequation[1]:\n", equation[1])
        #input("press any key to continue 5")
        equation[1].solve_milp()
        #input("press any key to continue 6")
        if equation[0].is_integer_solution():
            self.__update_UB(equation[0])
        if equation[1].is_integer_solution():
            self.__update_UB(equation[1])
        return equation


    def solve_algorithem(self):
        """
        run the branch and bound algorithm to find the best solution for the equation
        """
        next_node = self.tree.get_queue_head()
        while next_node:
            equation = self.init_BB_equation(next_node)
            if equation:
                self.tree.add_nodes(next_node, equation[0], equation[1])
                # print("LB = ", self.LB, ", UB = ", self.UB, "\n", self.tree)
                # print("LB = ", self.LB, ", UB = ", self.UB, "\n")
                # input("press any key to continue 7")
                next_node = self.__try_bound()
        #print("LB = ", self.LB, ", UB = ", self.UB, "\n", self.tree)
        print("UB = ", self.UB)
        self.best_equation.print_cplex_solution()