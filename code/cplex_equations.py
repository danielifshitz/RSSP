import cplex
from cplex.exceptions import CplexError

class Equations:
    obj = []
    ub = []
    lb = []
    ctype = ""
    colnames = []
    rownames = []
    sense = ""
    num_of_x = 0

    def __init__(self, cols, rows, vals, rhs, cols_to_remove, all_choices={}, new_choices={}):
        """
        cols: list of numbers, cols list for cplex
        rows: list of numbers, rows list for cplex
        vals: list of numbers, vals list for cplex
        rhs: string, rhs for cplex
        cols_to_remove: list of strings, all the Xi,m,r,l that not set yet
        all_choices: dict, choices that already made
        new_choices: dict, parametere name : choice value
        """
        if new_choices:
            variables_id = []
            index = 0
            for x, choice in new_choices.items():
                all_choices[x] = choice
                cols_to_remove.remove(x)
                variables_id.append(Equations.colnames.index(x))

            while index < len(cols):
                if cols[index] in variables_id:
                    col = cols.pop(index)
                    row = rows.pop(index)
                    val = vals.pop(index)
                    rhs[row] -= val * new_choices[Equations.colnames[col]]
                else:
                    index += 1
        self.rhs = rhs
        self.rows = rows
        self.cols = cols
        self.vals = vals
        self.cols_to_remove = cols_to_remove
        self.choices = all_choices
        self.integer_solution = False
        self.solution = None


    @staticmethod
    def init_global_data(obj, ub, lb, ctype, colnames, rownames, sense, num_of_x):
        Equations.obj = obj
        Equations.ub = ub
        Equations.lb = lb
        Equations.ctype = ctype
        Equations.colnames = colnames
        Equations.rownames = rownames
        Equations.sense = sense
        Equations.num_of_x = num_of_x


    def __populatebynonzero(self, prob):
        # prob.parameters.mip.limits.nodes.set(1)
        prob.objective.set_sense(prob.objective.sense.minimize)
        prob.linear_constraints.add(rhs=self.rhs, senses=Equations.sense,
                                    names=Equations.rownames)
        prob.variables.add(obj=Equations.obj, lb=Equations.lb, ub=Equations.ub, types=Equations.ctype,
                           names=Equations.colnames)
        prob.linear_constraints.set_coefficients(zip(self.rows, self.cols, self.vals))


    def print_cplex_data(self, prob, time, file_name=None):
        epgap = prob.parameters.mip.tolerances.mipgap.get()
        epagap = prob.parameters.mip.tolerances.absmipgap.get()
        print("Solution pool: {0} solutions saved.".format(
            prob.solution.pool.get_num()))
        print("MIP - {0} ({1}/{2}): Objective = {3:19.10e}".format(
            prob.solution.get_status_string(), epgap, epagap,
            prob.solution.get_objective_value()))
        left = prob.solution.progress.get_num_nodes_remaining()
        if left > 0:
            print("Solution time = {:.2} sec.  Iterations = {}  Nodes = {} ({})".format(
                time, prob.solution.progress.get_num_iterations(),
                prob.solution.progress.get_num_nodes_processed(), left))
        else:
            print("Solution time = {:.2} sec.  Iterations = {}  Nodes = {}".format(
                time, prob.solution.progress.get_num_iterations(),
                prob.solution.progress.get_num_nodes_processed()))
        print("Deterministic time = {:.2} ({:.2} ticks/sec)".format(
            prob.get_dettime(), prob.get_dettime()/time))
        if file_name:
            prob.write(file_name)


    def solve_milp(self, file_name=None):
        try:
            prob = cplex.Cplex()
            prob.set_warning_stream(None)
            prob.set_results_stream(None)
            prob.set_error_stream(None)
            self.__populatebynonzero(prob)
            # start = prob.get_time()
            prob.solve()
            # time = prob.get_time() - start
            # self.print_cplex_data(prob, time, file_name)
        except CplexError as exc:
            print(exc)
            input("press any key to continue")
            return None
        status = prob.solution.get_status()
        if status != 101:
            # Not mixed-integer problems solution
            # print("Solution status = ", status, ":", end=' ')
            # print(prob.solution.status[prob.solution.get_status()])
            self.integer_solution = True
            return None
        x = prob.solution.get_values()
        self.solution = prob.solution.get_objective_value()
        self.integer_solution = True
        for j in range(self.num_of_x):
            if not round(x[j],10).is_integer():
                self.integer_solution = False
                break
        prob.end()
        return self.solution

    
    def print_cplex_solution(self):
        try:
            prob = cplex.Cplex()
            self.__populatebynonzero(prob)
            # start = prob.get_time()
            prob.solve()
            # time = prob.get_time() - start
            # self.print_cplex_data(prob, time)
        except CplexError as exc:
            print(exc)
            return None
        numcols = prob.variables.get_num()
        x = prob.solution.get_values()
        for j in range(numcols):
            if self.colnames[j] not in self.choices:
                self.choices[self.colnames[j]] = round(x[j],3)
        prob.end()
        return self.choices
