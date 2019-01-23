from bisect import insort
from node import Node

class Tree:
    def __init__(self, equation, solution_type="minimize"):
        Node.solution_type = solution_type
        self.root = Node(equation)
        self.queue = [self.root]


    def add_nodes(self, father, left_equations, right_equations):
        """
        add 2 sons to the father node.
        add the new nodes to the queue if they are not leafs
        father: node
        left: node, left son
        right: node, right son
        return: none
        """
        left = Node(left_equations, father)
        right = Node(right_equations, father)
        father.add_sons(left, right)
        if not left.is_leaf():
            insort(self.queue, left)
        if not right.is_leaf():
            insort(self.queue, right)


    def get_queue_head(self):
        """
        return the first node in the queue, None if the queue empty
        return: node or None
        """
        if self.queue:
            return self.queue.pop(0)
        else:
            return None


    def __str__(self):
        queue_data = "{"
        for node in self.queue:
            queue_data += "\n\t{}".format(node)
        queue_data += "\n}"
        stars = "******************************************************************\n"
        return "{}tree: {}\n\nqueue: {}\n{}".format(stars, self.root, queue_data, stars)