from cplex_equations import Equations
from tree import Tree
from cplex import infinity
from concurrent import futures
from threading import Semaphore, active_count, Lock

class B_and_B():

    def __init__(self, obj, ub, lb, ctype, colnames, rhs, rownames, sense, rows, cols, vals, x_names, UB=float("inf"), use_SP=True, queue_limit=infinity):
        self.UB_lock = Lock()
        self.finished_semaphore = Semaphore(0)
        self.running_semaphore = Semaphore(0)
        self.best_equation = None
        self.number_of_best_solutions = 0
        Equations.init_global_data(obj, ub, lb, ctype, colnames, rownames, sense, len(x_names))
        self.tree = Tree(queue_limit)
        self.UB = UB
        self.use_SP = use_SP
        if use_SP:
            self.__create_SPs(1, rhs, rows, cols, vals, x_names)
            # print([round(node.get_solution(),3) for node in self.tree.queue])
        else:
            equation = Equations(cols, rows, vals, rhs, x_names, {}, {})
            # increase the number of the node in the queue by 1 by release the semaphore
            self.running_semaphore.release()
            self.__init_equation(equation, file_name="problem.lp")


    def __create_SPs(self, op, rhs, rows, cols, vals, x_names, needed_x=[]):
        """
        recursive function, for every SP take all operations and choice one mode.
        all SPs must be difference.
        """
        mode = 1
        sub = [s for s in x_names if "X" + str(op)+ "," +str(mode) in s]
        while sub:
            needed_x_copy = needed_x[:]
            needed_x_copy += sub
            self.__create_SPs(op + 1, rhs, rows, cols, vals, x_names, needed_x_copy)
            mode += 1
            sub = [s for s in x_names if "X" + str(op)+ "," +str(mode) in s]
        if not [s for s in x_names if "X" + str(op) in s]:
            equation = Equations(cols[:], rows[:], vals[:], rhs[:], x_names[:],{},
                {elem : 0 for elem in x_names if elem not in needed_x})
            self.running_semaphore.release()
            self.__init_equation(equation)


    def __update_UB(self, equation):
        """
        check the equation solution and if it's better then the UB, update UB,
        save the equation and set the number of the solutions to one.
        if its equals to the UB increase the number of the solutions.
        use lock to check the UB to avoid conflicts.
        equatiosn: Equation, an equation with integer solution
        return: None
        """
        self.UB_lock.acquire()
        solution = equation.solution
        print("found UB that is eqauls to", solution)
        if solution and solution < self.UB:
            self.UB = solution
            self.best_equation = equation
            self.number_of_best_solutions = 1
        elif solution and solution == self.UB:
            self.number_of_best_solutions += 1
        self.UB_lock.release()


    def __try_bound(self):
        """
        try to take node from the queue, if its solution worth then the UB drop this node,
        repeat until node solution better or equals to the UB or until the queue is empty.
        if the queue is empty but there are threads that not finished yet, wait for them.
        return: Node if fuond better or equals solution then UB or None if the queue is empty
        """
        # if there are running or finished thread, try decrease the number of nodes in the queue by acquire semaphore
        if self.finished_semaphore._value or self.running_semaphore._value:
            self.finished_semaphore.acquire()
        next_node = self.tree.get_queue_head()
        while next_node: # while the queue not empty
            # if the node worth then the UB, take another node
            if next_node.get_solution() > self.UB:
                # if there are running or finished thread, try decrease the number of nodes in the queue by acquire semaphore
                if self.finished_semaphore._value or self.running_semaphore._value:
                    self.finished_semaphore.acquire()
                next_node = self.tree.get_queue_head() # take another node from the queue
            else:
                return next_node
        # return None if the queue is empty and all the tree was bound
        return None


    def __init_equation(self, equation, depth=0, file_name=None):
        """
        create new node from the equation and add it to the queue.
        after the node was created, release semaphore as sign that there is new node in the queue.
        equation: Equation, cplex equation
        depth: int, next node depth
        file_name: string, where save the cplex solution, or None
        return: None
        """
        # solve LP using cplex
        solution = equation.solve_milp(file_name)
        # if the solution is integer, check the UB
        if solution and equation.integer_solution:
            self.__update_UB(equation)
        # if the solution better or equals to the UB, save it in the queue
        elif solution and solution <= self.UB:
            self.tree.add_nodes(equation, depth)
            # increase the number on nodes in the queue by 1
            self.finished_semaphore.release()
        # else, drop it, this node is not needed
        # decrease the number of running threads
        self.running_semaphore.acquire()
        # if there are no more running or finished thread, wake up the __try_bound function by increase the finished thread semaphore
        if not self.finished_semaphore._value and not self.running_semaphore._value:
            self.finished_semaphore.release()
    
    
    def create_node(self, node, col_dict):
        """
        create new equation, solve it and add it to the B&B queue
        node: Node, father node
        col_dict: dict, a dict of parameters name and the selected value for them
        return: None
        """
        eq = node.equation
        equation = Equations(eq.cols[:], eq.rows[:], eq.vals[:],
            eq.rhs[:], eq.cols_to_remove[:], eq.choices.copy(), col_dict)
        self.__init_equation(equation, node.depth + 1)


    def set_x_to_one(self, node, x_one):
        """
        take all the not set Xi,m,r,l from the node and set the chosen Xi,m,r,l to
        value of one and set all blocked (by the equations) Xi,m,r,l to zero.
        all the choices will be save at a dictionary that will contain Xi,m,r,l : chosen value
        node: Node, from that node we will create new node
        x_one: string, the chosen Xi,m,r,l
        return None
        """
        choices = {}
        choices[x_one] = 1
        i, m, r, l = x_one[1:].split(",")
        # if Xi,m,r,l = 1
        for x in node.equation.cols_to_remove:
            other_i, other_m, other_r, other_l = x[1:].split(",")
            # Xj,n,t,k = 0 | j = i, n = m, t = r and k != l
            if i == other_i and m == other_m and r == other_r and l != other_l:
                choices[x] = 0
            # Xj,n,t,k = 0 | j != i, n = or != m, t = r and k = l
            elif i != other_i and r == other_r and l == other_l:
                choices[x] = 0
            # Xj,n,t,k = 0 | j = i, n != m, t = or != r and k = or != l
            elif i == other_i and m != other_m:
                choices[x] = 0
        self.create_node(node, choices)


    # def choice_resource(self, node):
    #     i, m, r = node.equation.cols_to_remove[0][1:-2].split(",")
    #     zero_choices = {}
    #     for x in node.equation.cols_to_remove:
    #         other_i, other_m, other_r = x[1:-2].split(",")
    #         if i == other_i and m == other_m and r == other_r:
    #             self.running_semaphore.release()
    #             self.set_x_to_one(node, x)
    #             zero_choices[x] = 0
    #     if not self.use_SP:
    #         self.running_semaphore.release()
    #         self.create_node(node, zero_choices)
    #     self.running_semaphore.acquire()
    #     if not self.finished_semaphore._value and not self.running_semaphore._value:
    #         self.finished_semaphore.release()


    def solve_algorithem(self, workers=2, disable_prints=True):
        """
        run the branch and bound algorithm to find the best solution for the equation.
        use threads if the queue is bigger than the queue limit.
        every time we want to create new node we need to increase the number of running threads semaphore.
        after the node where created/began to created, take node from the queue.
        when the queue is empty and the algorithm end, solve the best equation one more time
        to get all the chosen value for the Xi,m,r,l.
        workers: number of thread in the thread pool
        return: dict, string: dict - the parameters name and chosen values,
            string - number of created nodes, max depth and max queue size
        """
        # decrease the number of the node in the queue by 1 by acquire the semaphore
        self.finished_semaphore.acquire()
        next_node = self.tree.get_queue_head()
        # create thread pool
        with futures.ThreadPoolExecutor(max_workers=workers) as executor:
            # run while the node not None which mean that the algorithm not end
            while next_node:
                # TODO check if this condition is necessary
                if next_node.equation.cols_to_remove:
                    # we create 2 new nodes so we increase the number of running threads by 2
                    self.running_semaphore.release()
                    self.running_semaphore.release()
                    # create dictionary with one Xi,m,r,l equals to zero
                    col_dict = {next_node.equation.cols_to_remove[0] : 0}
                    # if threads needed, use executor to add the jobs to thread pool
                    if self.tree.use_threads:
                        # son with Xi,m,r,l = 0
                        executor.submit(self.create_node, next_node, col_dict)
                        # son with Xi,m,r,l = 1
                        executor.submit(self.set_x_to_one, next_node, next_node.equation.cols_to_remove[0])
                    else:
                        # son with Xi,m,r,l = 0
                        self.create_node(next_node, col_dict)
                        # son with Xi,m,r,l = 1
                        self.set_x_to_one(next_node, next_node.equation.cols_to_remove[0])
                    # self.running_semaphore.release()
                    # if self.tree.use_threads:
                    #     executor.submit(self.choice_resource, next_node)
                    # else:
                    #     self.choice_resource(next_node)
                # check if we can do bound on the tree and take next node from the queue
                next_node = self.__try_bound()
        solution_data = "created nodes = {}, max depth = {}, max queue size = {}".format(self.tree.num_of_nodes,
            self.tree.max_depth, self.tree.max_queue_size)
        try:
            print("number of best solutions =", self.number_of_best_solutions)
            return self.best_equation.cplex_solution(disable_prints), solution_data
        except:
            print("cann't find integer solution")
            return None, None