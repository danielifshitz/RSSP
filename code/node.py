class Node:

    def __init__(self, equation, depth=0):
        self.equation = equation
        self.depth = depth


    def is_leaf(self):
        """
        return True if the node is the leaf (sons = [None, None]), Flase otherwise
        return: boolean
        """
        return self.equation.integer_solution


    def get_solution(self):
        """
        return node's value, which calculeted at Equations
        return: float
        """
        return self.equation.solution


    def __lt__(self, other):
        """
        comper this node and other node Based on Equations value
        return True is this node less the other node, Flase otherwise
        return: boolean
        """
        if self.get_solution() == other.get_solution():
            return self.depth >= other.depth
        return self.get_solution() < other.get_solution()
