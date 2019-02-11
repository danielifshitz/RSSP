class Node:

    def __init__(self, equation, father=None):
        self.equation = equation
        if not father:
            self.depth = 0
        else:
            self.depth = father.depth + 1


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
        return self.equation.solution


    def __lt__(self, other):
        """
        comper this node and other node Based on Equations value
        return True is this node less the other node, Flase otherwise
        return: boolean
        """
        return other.get_value() >= self.get_value()
