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


    def get_solution(self):
        return self.solution


    def is_integer_solution(self):
        return self.integer_solution


    def __populatebynonzero(self, prob):
        prob.objective.set_sense(prob.objective.sense.minimize)
        #self.prob.objective.set_sense(self.prob.objective.sense.maximize)
        prob.linear_constraints.add(rhs=self.rhs, senses=Equations.sense,
                                    names=Equations.rownames)
        prob.variables.add(obj=Equations.obj, lb=Equations.lb, ub=Equations.ub, types=Equations.ctype,
                           names=Equations.colnames)
        # print("number of integers =", prob.variables.get_num_integer())
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
        # the following line prints the corresponding string
        self.solution = prob.solution.get_objective_value()
        # print("Solution value  = ", self.solution)
        self.integer_solution = True
        for j in range(self.num_of_x):
            if not round(x[j],10).is_integer():
                self.integer_solution = False
                # print(x)
                break
        # print("integer_solution =", self.integer_solution)
        prob.end()
        return self.solution

    
    def print_cplex_solution(self):
        print("\n\nsolution!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n")
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
        status = prob.solution.get_status()
        print("Solution status = ", status, ":", end=' ')
        print(prob.solution.status[prob.solution.get_status()])
        print("Solution value = %10f" % prob.solution.get_objective_value())
        numcols = prob.variables.get_num()
        x = prob.solution.get_values()
        for j in range(numcols):
            if self.colnames[j] in self.choices:
                print("variable %s:  Value = %10f" % (self.colnames[j], self.choices[self.colnames[j]]))
            else:
                self.choices[self.colnames[j]] = round(x[j],3)
                print("variable %s:  Value = %10f" % (self.colnames[j], x[j]))
        # print(self.choices) # need!!!!
        prob.end()
        return self.choices


    def create_sons_equations(self, col_name):
        cols_to_remove = self.cols_to_remove[:]
        zero_rhs = self.rhs[:]
        one_rhs = self.rhs[:]
        cols = self.cols[:]
        rows = self.rows[:]
        vals = self.vals[:]
        zero_choices = self.choices.copy()
        zero_choices[col_name] = 0
        one_choices = self.choices.copy()
        one_choices[col_name] = 1
        cols_to_remove.remove(col_name)
        variable_id = self.colnames.index(col_name)
        index = 0
        while index < len(cols):
            if cols[index] == variable_id:
                cols.pop(index)
                row = rows.pop(index)
                val = vals.pop(index)
                one_rhs[row] -= val
            else:
                index += 1
        equations = []
        equations.append(Equations(zero_rhs, rows, cols, vals, cols_to_remove, zero_choices))
        equations.append(Equations(one_rhs, rows, cols, vals, cols_to_remove, one_choices))
        return equations

