from bisect import insort
from node import Node

class Tree:

    def __init__(self):
        self.queue = []
        self.max_queue_size = 0
        self.num_of_nodes = 0
        self.max_depth = 0


    def add_nodes(self, father, equation): #left_equations, right_equations):
        """
        add 2 sons to the father node.
        add the new nodes to the queue if they are not leafs
        father: node
        left: node, left son
        right: node, right son
        return: none
        """
        if father and father.depth >= self.max_depth:
            self.max_depth += 1
        node = Node(equation, father)
        self.num_of_nodes += 1
        if not node.is_leaf():
            insort(self.queue, node)
        if self.max_queue_size != len(self.queue):
            self.max_queue_size = len(self.queue)
            print("queue size =", self.max_queue_size)
            print("num of nodes =", self.num_of_nodes)
        # print the status of the solution every 100 nodes
        elif self.num_of_nodes % 100 == 1:
            print("queue size =", len(self.queue))
            print("num of nodes =", self.num_of_nodes)


    def get_queue_head(self):
        """
        return the first node in the queue, None if the queue empty
        return: node or None
        """
        if self.queue:
            return self.queue.pop(0)
        else:
            return None
