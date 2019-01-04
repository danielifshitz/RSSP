class Node:
    number = 0

    def __init__(self, equations, father=None):
        self.father = father
        self.equations = equations
        if equations.is_integer_sulotion():
            self.sons = [None, None]
        else:
            self.sons = [-1,-1]
        if not father:
            self.depth = 0
        else:
            self.depth = father.depth + 1
        self.name = Node.number
        Node.number += 1


    def add_sons(self, left, right):
        """
        add 2 sons to the node
        left: node, left son
        right: node, right son
        return: none
        """
        self.sons = []
        self.sons.append(left)
        self.sons.append(right)


    def is_root(self):
        """
        return True if the node is the root (no father), Flase otherwise
        return: boolean
        """
        return self.father is None


    def is_leaf(self):
        """
        return True if the node is the leaf (sons = [None, None]), Flase otherwise
        return: boolean
        """
        return not (self.get_left_son() or self.get_right_son())


    def get_left_son(self):
        """
        return node's left son
        return: Node
        """
        return self.sons[0]


    def get_right_son(self):
        """
        return node's right son
        return: Node
        """
        return self.sons[1]


    def get_value(self):
        """
        return node's value, which  calculeted at Equations
        return: float
        """
        return self.equations.get_solution()


    def __lt__(self, other):
        """
        comper this node and other node Based on Equations value
        return True is this node less the other node, Flase otherwise
        return: boolean
        """
        return other.get_value() > self.get_value()


    def __str__(self):
        if self.is_leaf():
            sons_data = "None"
        else:
            tabs = ""
            for i in range(0, self.depth):
                tabs += "\t"
            sons_data = "["
            for son in self.sons:
                sons_data += "\n{}\t{}".format(tabs, son)
            sons_data += "\n{}]".format(tabs)
        if self.father is None:
            return "node {}: father = {}, equations = {}, sons = {}".format(self.name, self.father, self.equations, sons_data)
        else:
            return "node {}: father = {}, equations = {}, sons = {}".format(self.name, self.father.name, self.equations, sons_data)