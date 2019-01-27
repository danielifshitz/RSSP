import cplex
from cplex.exceptions import CplexError

class Equations:

    def __init__(self, obj, ub, lb, ctype, colnames, rhs, rownames, sense, rows, cols, vals, cols_to_remove, num_of_x, choices):
        self.prob = cplex.Cplex()
        self.prob.set_warning_stream(None)
        self.prob.set_results_stream(None)
        self.prob.set_error_stream(None)
        self.obj = obj
        self.ub = ub
        self.lb = lb
        self.ctype = ctype
        self.colnames = colnames
        self.rhs = rhs
        self.rownames = rownames
        self.sense = sense
        self.rows = rows
        self.cols = cols
        self.vals = vals
        self.cols_to_remove = cols_to_remove
        self.num_of_x = num_of_x
        self.choices = choices
        self.integer_solution = False
        self.solution = None


    def get_solution(self):
        return self.solution


    def is_integer_solution(self):
        return self.integer_solution


    def __populatebynonzero(self):
        self.prob.objective.set_sense(self.prob.objective.sense.minimize)
        #self.prob.objective.set_sense(self.prob.objective.sense.maximize)
        self.prob.linear_constraints.add(rhs=self.rhs, senses=self.sense,
                                    names=self.rownames)
        self.prob.variables.add(obj=self.obj, lb=self.lb, ub=self.ub, types=self.ctype,
                           names=self.colnames)
        self.prob.linear_constraints.set_coefficients(zip(self.rows, self.cols, self.vals))


    def solve_milp(self):
        try:
            self.__populatebynonzero()
            self.prob.solve()
        except CplexError as exc:
            print(exc)
            return None
        # print()
        # solution.get_status() returns an integer code
        status = self.prob.solution.get_status()
        # print("Solution status = ", status, ":", end=' ')
        # print(self.prob.solution.status[self.prob.solution.get_status()])
        if status != 101:
            # Not mixed-integer problems solution
            self.integer_solution = True
            return None
        # the following line prints the corresponding string
        self.solution = self.prob.solution.get_objective_value()
        # print("Solution value  = ", self.solution)
        numcols = self.prob.variables.get_num()
        x = self.prob.solution.get_values()
        self.integer_solution = True
        for j in range(numcols):
            # print("variable %d:  Value = %10f" % (j, x[j]))
            if not x[j].is_integer():
                self.integer_solution = False
            if j >= self.num_of_x - 1:
                break
        # print(x)
        # print(self.integer_solution)
        # print(self.num_of_x)
        return self.solution

    
    def print_cplex_solution(self):
        status = self.prob.solution.get_status()
        print("Solution status = ", status, ":", end=' ')
        print(self.prob.solution.status[self.prob.solution.get_status()])
        print("Solution value  = ", self.prob.solution.get_objective_value())
        numcols = self.prob.variables.get_num()
        x = self.prob.solution.get_values()
        for j in range(numcols):
            if self.colnames[j] in self.choices:
                print("variable %s:  Value = %10f" % (self.colnames[j], self.choices[self.colnames[j]]))
            else:
                self.choices[self.colnames[j]] = x[j]
                print("variable %s:  Value = %10f" % (self.colnames[j], x[j]))
        print(self.choices)
        self.prob.write("solution.lp")


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
        equations.append(Equations(self.obj, self.ub, self.lb, self.ctype,self.colnames, zero_rhs, self.rownames,
                                                   self.sense, rows, cols, vals, cols_to_remove, self.num_of_x, zero_choices))
        equations.append(Equations(self.obj, self.ub, self.lb, self.ctype,self.colnames, one_rhs, self.rownames,
                                                   self.sense, rows, cols, vals, cols_to_remove, self.num_of_x, one_choices))
        return equations


    def __str__(self):
        """
        print("data:\n", self.obj, "\n", self.ub, "\n", self.lb, "\n", self.ctype, "\n",
               self.colnames, "\n", self.rhs, "\n", self.rownames, "\n", self.sense, "\n",
               self.rows, "\n", self.cols, "\n", self.vals, "\n\n")
        """
        string = "Maximize "
        string += str(self.obj) + "\n"
        string += "Subject to\n"
        last_row = self.rows[0]
        for i in range(len(self.rows)):
            if self.rows[i] > last_row:
                if self.sense[last_row] == "E":
                    string += "= "
                elif self.sense[last_row] == "L":
                    string += "<= "
                elif self.sense[last_row] == "G":
                    string += ">= "
                string += str(self.rhs[last_row]) + "\n"
                last_row = self.rows[i]
            string += str(self.vals[i]) + " x" + str(self.cols[i]) + " "
        if self.sense[last_row] == "E":
            string += "= "
        elif self.sense[last_row] == "L":
            string += "<= "
        elif self.sense[last_row] == "G":
            string += ">= "
        string += str(self.rhs[last_row]) + "\n"
        string += "Bounds\n"
        for i in range(len(self.colnames)):
            string += str(self.lb[i]) + " <= " + self.colnames[i] + " <= " + str(self.ub[i]) + "\n"
        string += "types " + str(self.ctype) + "\n"
        string += "sense " + str(self.sense) + "\n"
        return string
