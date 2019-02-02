class Node:

    number = 0
    solution_type = "minimize"

    def __init__(self, equation, father=None):
        # self.father = father
        self.equation = equation
        if not father:
            self.depth = 0
        else:
            self.depth = father.depth + 1
        self.name = Node.number
        Node.number += 1


    def is_leaf(self):
        """
        return True if the node is the leaf (sons = [None, None]), Flase otherwise
        return: boolean
        """
        return self.equation.integer_solution


    def get_value(self):
        """
        return node's value, which  calculeted at Equations
        return: float
        """
        return self.equation.get_solution()


    def __lt__(self, other):
        """
        comper this node and other node Based on Equations value
        return True is this node less the other node, Flase otherwise
        return: boolean
        """
        if Node.solution_type == "minimize":
            return other.get_value() > self.get_value() # minimize
        else:
            return other.get_value() < self.get_value() # maximize
