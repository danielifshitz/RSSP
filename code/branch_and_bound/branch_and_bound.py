from tree import Tree
from equations import Equations

class B_and_B():
    UB = float("inf")
    LB = float("inf")
	best_equation = None

    def __init__(self, root_equations):
        equations = Equations(root_equations)
        B_and_B.LB = equations.get_solution()
        self.tree = Tree(equations)


    def __update_UB(self, equation):
		"""
		check the equation and if their solution better then the UB, update UB and save the equation
		equation: Equation, the equation of a node
		return: None
		"""
        if equation.get_solution() < B_and_B.UB:
            B_and_B.UB = equation.get_solution()
			B_and_B.best_equation = equation


    def __try_bound(self):
		"""
		take the next node in the queue, if its solution worth then the UB drop this node
		repeat until node solution better then the UB or until the queue is empty
		return: Node if fuond better solution then UB or None if the queue is empty
		"""
        next_node = self.tree.get_queue_head()
        while next_node: # while the queue not empty
            if next_node.get_value() > B_and_B.UB:
                print("node ", next_node.name, " with value ", next_node.get_value(), " bounded")
                next_node = self.tree.get_queue_head() # take another node from the queue
            else:
                return next_node
        return None
    
    
    def init_BB_equation(self, array, index):
		"""
		only for testing, will be deleted
		"""
        value = array[index][0]
        leaf = array[index][1]
        equation = Equations(value, leaf)
        if equation.is_integer_sulotion():
            self.__update_UB(equation)
        return equation


    def solve_algorithem(self, array):
		"""
		run the branch and bound algorithm to find the best solution for the equation 
		"""
        index = 0
        next_node = self.tree.get_queue_head()
        while next_node:
            left = self.init_BB_equation(array, index)
            index += 1
            right = self.init_BB_equation(array, index)
            index += 1
            self.tree.add_nodes(next_node, left, right)
            print("LB = ", B_and_B.LB, ", UB = ", B_and_B.UB, "\n", self.tree)
            input("press any key to continue")
            next_node = self.__try_bound()
        print("LB = ", B_and_B.LB, ", UB = ", B_and_B.UB, "\n", self.tree)