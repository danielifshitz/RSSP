import heapq
from node import Node

class Tree:

    def __init__(self):
        self.queue = []
        self.max_queue_size = 0
        self.num_of_nodes = 0
        self.next_ten_thousand = 1

    def add_nodes(self, equation, depth=0):
        """
        add new node to the sorted queue.
        insert the new node to the queue if it is not leaf (integer solution)
        equation: Equation, equation for the son node
        depth: father depth
        return: none
        """
        # create new node and increase the number of created nodes by one
        node = Node(equation, depth)
        self.num_of_nodes += 1
        # if self.num_of_nodes >= self.next_ten_thousand * 1000:
        #     print("num_of_nodes =", self.num_of_nodes)
        #     self.next_ten_thousand += 1
        # add new node to the queue only if node solution's isn't integer solution
        if not node.is_leaf():
            heapq.heappush(self.queue, node)
        # save max queue size
        self.max_queue_size = max(self.max_queue_size, len(self.queue))
        # print("max queue size =", self.max_queue_size)
        # print("node solution =", node.get_solution())
        # print("num of nodes =", self.num_of_nodes)
        # print("queue size =", len(self.queue))
        # print("queue = ", [{item.get_solution() : item.depth} for item in self.queue])


    def get_queue_head(self):
        """
        return the first node in the queue, None if the queue empty
        return: Node or None
        """
        if self.queue:
            return self.queue.pop(0)
