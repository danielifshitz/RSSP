from bisect import insort
from node import Node
from threading import Lock

class Tree:

    def __init__(self, queue_limit):
        self.lock = Lock()
        self.queue = []
        self.max_queue_size = 0
        self.num_of_nodes = 0
        self.max_depth = 0
        self.queue_limit = queue_limit
        self.use_threads = False

    def add_nodes(self, equation, depth=0):
        """
        add new node to the sorted queue.
        insert the new node to the queue if it is not leaf (integer solution)
        use lock because only one thread can access to the queue at the same time
        equation: Equation, equation for the son node
        depth: father depth
        return: none
        """
        # save the max depth
        if depth == self.max_depth:
            self.max_depth = depth + 1
        # create new node and increase the number of created nodes by one
        node = Node(equation, depth)
        self.num_of_nodes += 1
        # add new node to the queue only if node solution's isn't integer solution
        if not node.is_leaf():
            # lock the queue
            self.lock.acquire()
            insort(self.queue, node) # O(log(n))
            # release the queue
            self.lock.release()
        # if the queue size is bigger then the queue limit, turn on thread flag
        if self.queue_limit < len(self.queue) and not self.use_threads:
            self.use_threads = True
        # if the queue size is less then the 10% of queue limit, turn off thread flag
        elif self.queue_limit % 10 > len(self.queue) and self.use_threads:
            self.use_threads = False
        # save max queue size
        if self.max_queue_size < len(self.queue):
            self.max_queue_size = len(self.queue)
        # print("max queue size =", self.max_queue_size)
        # print("node solution =", node.get_solution())
        # print("num of nodes =", self.num_of_nodes)
        # print("queue size =", len(self.queue))
        # print("queue = ", [{item.get_solution() : item.depth} for item in self.queue])


    def get_queue_head(self):
        """
        return the first node in the queue, None if the queue empty
        use lock because only one thread can access to the queue at the same time
        return: Node or None
        """
        self.lock.acquire()
        head = None
        if self.queue:
            head = self.queue.pop(0)
        self.lock.release()
        return head
