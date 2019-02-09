from bisect import insort
from node import Node

class Tree:

    def __init__(self):
        self.queue = []
        self.max_queue_size = 0
        self.num_of_nodes = 0
        self.max_depth = 0


    def add_node(self, father, equation):
        """
        add new node under father node.
        insert the new node to the queue if it is not leaf (integer solution)
        father: Node
        equation: Equation
        return: none
        """
        if father and father.depth >= self.max_depth:
            self.max_depth += 1
        node = Node(equation, father)
        self.num_of_nodes += 1
        # check if the new node have integer solution
        if not node.is_leaf():
            insort(self.queue, node)
        # print the status of the solution if queue size changed
        if self.max_queue_size != len(self.queue):
            self.max_queue_size = len(self.queue)
            print("queue size =", self.max_queue_size)
            print("num of nodes =", self.num_of_nodes)
            print("queue = ", [item.get_value() for item in self.queue])
        # print the status of the solution every 100 nodes
        elif self.num_of_nodes % 100 == 1:
            print("queue size =", len(self.queue))
            print("num of nodes =", self.num_of_nodes)
            print("queue = ", [item.get_value() for item in self.queue])


    def get_queue_head(self):
        """
        return the first node in the queue, None if the queue empty
        return: Node or None
        """
        if self.queue:
            return self.queue.pop(0)
        else:
            return None
