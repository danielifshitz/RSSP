import cplex
from cplex.exceptions import CplexError

class Equations:

    """
    in this class we will solve the LP using the cplex
    all problem data will be saved here and will be send to the cplex
    """

    obj = []
    ub = []
    lb = []
    ctype = ""
    colnames = []
    rownames = []
    sense = ""
    num_of_x = 0
    MIP_infeasible = False

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
            # save all changed variables id(index)
            for x, choice in new_choices.items():
                all_choices[x] = choice
                cols_to_remove.remove(x)
                variables_id.append(Equations.colnames.index(x))

            while index < len(cols):
                if cols[index] in variables_id:
                    col = cols.pop(index)
                    row = rows.pop(index)
                    val = vals.pop(index)
                    # calculate the right side of the equation value according a parameter choisen value
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
        """
        this parameters are will not changed throughout the algorithm run.
        """
        Equations.obj = obj
        Equations.ub = ub
        Equations.lb = lb
        Equations.ctype = ctype
        Equations.colnames = colnames
        Equations.rownames = rownames
        Equations.sense = sense
        Equations.num_of_x = num_of_x
        Equations.MIP_infeasible = False


    def __populatebynonzero(self, prob, disable_prints=True):
        """
        set problem data, acording to the cplex documentation.
        prob: Cplex.Cplex, the cplex object
        disable_prints: boolean, disable prints or not
        return: None
        """
        if disable_prints:
            prob.set_warning_stream(None)
            prob.set_results_stream(None)
            prob.set_error_stream(None)

        # solve minimom problem
        prob.objective.set_sense(prob.objective.sense.minimize)
        # for each row, set its name, sign and the equation right side value (the side with the number)
        prob.linear_constraints.add(rhs=self.rhs, senses=Equations.sense,
                                    names=Equations.rownames)
        # set objective function, each variable type(integer of flout) and its limits
        prob.variables.add(obj=Equations.obj, lb=Equations.lb, ub=Equations.ub, types=Equations.ctype,
                           names=Equations.colnames)
        # set each parameter coefficients in each row and col
        prob.linear_constraints.set_coefficients(zip(self.rows, self.cols, self.vals))


    def solve_milp(self, file_name=None):
        try:
            prob = cplex.Cplex()
            # set problem data, as writen in the cplex documentation
            self.__populatebynonzero(prob)
            prob.solve()
            if file_name:
                prob.write(file_name)
        except CplexError as exc:
            print(exc)
            input("press any key to continue")
            return None

        status = prob.solution.get_status()
        if status != 101:
            # mixed-integer problems solution can't be found
            # if the status is 103, the problem is infeasible and can't be solved
            Equations.MIP_infeasible = Equations.MIP_infeasible or status == 103
            # set integer_solution = true because we want that the node that contanes this equations
            # will behave like if its was an integer solution.
            self.integer_solution = True
            return None

        x = prob.solution.get_values()
        # the cplex have some round number problem and instad of return
        # 1.0 it's may return 0.99999999998, to solve this problem we will
        # round numbers after the 10's digit
        self.solution = round(prob.solution.get_objective_value(),10)
        self.integer_solution = True
        # run on all Xi,m,r,l and check if all of them are integers number
        for j in range(self.num_of_x):
            # if even one of the Xi,m,r,l is not integer, set integer_solution to False
            if not round(x[j],10).is_integer():
                self.integer_solution = False
                break

        prob.end()
        return self.solution

    
    def cplex_solution(self, disable_prints):
        """
        this function solve and return an leaf solution data.
        disable_prints: boolean, disable prints or not.
        return: dictionary of all choices values for each Xi,m,r,l and number of nodes.
        """
        try:
            prob = cplex.Cplex()
            # set problem data, as writen in the cplex documentation
            self.__populatebynonzero(prob, disable_prints=disable_prints)
            prob.solve()

        except CplexError as exc:
            print(exc)
            return None

        numcols = prob.variables.get_num()
        x = prob.solution.get_values()
        # save all the choised values for each of the Xi,m,r,l
        for j in range(numcols):
            # if the Xi,m,r,l was not choised by the B&B, set its value
            # acording to the cplex solution
            if self.colnames[j] not in self.choices:
                self.choices[self.colnames[j]] = round(x[j],3)

        # save the number of nodes that the cplex used to solve the problem
        nodes = prob.solution.progress.get_num_nodes_processed()
        prob.end()
        return self.choices, nodes
