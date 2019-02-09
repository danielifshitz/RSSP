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

    def __init__(self, rhs, rows, cols, vals, cols_to_remove, choices):
        self.rhs = rhs
        self.rows = rows
        self.cols = cols
        self.vals = vals
        self.cols_to_remove = cols_to_remove
        self.choices = choices
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
            cplexlog = "cplex.log"
            prob.set_warning_stream(None)
            prob.set_results_stream(None)
            prob.set_error_stream(None)
            prob.set_log_stream(cplexlog)
            self.__populatebynonzero(prob)
            # start = prob.get_time()
            prob.solve()
            # time = prob.get_time() - start
        except CplexError as exc:
            print(exc)
            return None
        status = prob.solution.get_status()
        if status != 101:
            # Not mixed-integer problems solution
            # print("Solution status = ", status, ":", end=' ')
            # print(prob.solution.status[prob.solution.get_status()])
            self.integer_solution = True
            return None
        # self.print_cplex_data(prob, time, file_name)
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
            start = prob.get_time()
            prob.solve()
            time = prob.get_time() - start
            self.print_cplex_data(prob, time)
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


    def create_son_equations(self, col_dict):
        cols_to_remove = self.cols_to_remove[:]
        rhs = self.rhs[:]
        cols = self.cols[:]
        rows = self.rows[:]
        vals = self.vals[:]
        choices = self.choices.copy()
        variables_id = []
        for x, choice in col_dict.items():
            choices[x] = choice
            cols_to_remove.remove(x)
            variables_id.append(self.colnames.index(x))
        index = 0
        while index < len(cols):
            if cols[index] in variables_id:
                col = cols.pop(index)
                row = rows.pop(index)
                val = vals.pop(index)
                rhs[row] -= val * col_dict[self.colnames[col]]
            else:
                index += 1
        return Equations(rhs, rows, cols, vals, cols_to_remove, choices)
