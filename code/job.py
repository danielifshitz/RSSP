from job_operation import Operation
from job_resource import Resource
import equations
import csv
import cplex
import sys
from branch_and_bound import B_and_B
from cplex_equations import Equations

class Job:
    def __init__(self, csv_path):
        self.path = csv_path
        self.N = cplex.infinity
        self.resources = {}
        self.operations = {}
        self.preferences = {}
        self.cplex = {'obj' : [], 'ub' : [], 'lb' : [], 'ctype' : "", 'colnames' : [], 'rhs' : [], 
                      'rownames' : [], 'sense' : "", 'rows' : [], 'cols' : [], 'vals' : []}
        self.csv_problem()

    def csv_problem(self):
        """
        read from csv file the problem and initialize job attributes
        """
        with open(self.path, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                if row["resource"] not in self.resources:
                    self.resources[row["resource"]] = Resource(row["resource"])
                if row["operation"] not in self.operations:
                    self.operations[row["operation"]] = Operation(row["operation"])
                self.operations[row["operation"]].add_mode_to_operation(row["mode"], self.resources[row["resource"]], float(row["start"]), float(row["duration"]))
                for op in row["preferences"].split(";"):
                    if op:
                        if row["operation"] in self.preferences:
                            self.preferences[row["operation"]].append(self.operations[op])
                        else:
                            self.preferences[row["operation"]] = [self.operations[op]]
                    else:
                        self.preferences[row["operation"]] = None

            for op, preferences in self.preferences.items():
                if preferences:
                    self.preferences[op] = list(set(preferences))

        # create dictionary for cplex
        self.__find_rtag_tim()
        self.__init_cplex_variable_parameters()

    def __find_rtag_tim(self):
        """
        set the r' and the Tim for all modes
        return: None
        """
        for op in self.operations.values():
            for mode in op.modes:
                mode.find_rtag()
                mode.find_tim()

    def __init_cplex_variable_parameters(self):
        """
        initialize cplex data according to the problem data
        """
        # add all Xi,m,r,l to colnames list
        for operation in self.operations.values():
            for mode in operation.modes:
                # op_mode = operation.op_num + ',' + mode.num_mode
                for resource in mode.needed_resources:
                    for index in range(1, resource.size + 1):
                        name = "X{},{},{},{}".format(operation.num_of_op, mode.num_mode, resource.number, index)
                        self.cplex["colnames"].append(name)

        x_i_m_r_l_len = len(self.cplex["colnames"])
        # add all Ti to colnames list
        for index in range(1, len(self.operations) + 1):
            name = "T" + str(index)
            self.cplex["colnames"].append(name)

        # add all Tr,l to colnames list
        for resource in self.resources.values():
            for index in range(1, resource.size + 1):
                name = "T" + str(resource.number) + ',' + str(index)
                self.cplex["colnames"].append(name)

        # add C to colnames list
        self.cplex["colnames"].append("C")

        # initialize ctype
        self.cplex["ctype"] = 'C' * len(self.cplex["colnames"])

        # initialize lb
        self.cplex["lb"] = [0] * len(self.cplex["colnames"])

        # initialize ub - Ximrl ub is 1. Ti and Tim and C ub is infinity
        self.cplex["ub"] = [1] * x_i_m_r_l_len
        self.cplex["ub"] += [cplex.infinity] * (len(self.cplex["colnames"]) - 1 - x_i_m_r_l_len)
        self.cplex["ub"].append(cplex.infinity)

        # initialize obj
        self.cplex["obj"] = [0] * (len(self.cplex["colnames"]) - 1)
        self.cplex["obj"].append(1)

    def __str__(self):
        string = ""
        for key, value in self.operations.items():
            string += str(key) + " : { " + str(value) + " \n}\n"
        return string

job1 = Job("data.csv")
equations.first_equations(job1.operations, job1.cplex)
equations.second_equations(job1.operations, job1.cplex)
equations.third_equations(job1.resources, job1.cplex)
equations.Fourth_equations(job1.operations, job1.preferences, job1.cplex)
print(job1.cplex)
# eq = Equations(job1.cplex["obj"], job1.cplex["ub"], job1.cplex["lb"], job1.cplex["ctype"], job1.cplex["colnames"], job1.cplex["rhs"], job1.cplex["rownames"], job1.cplex["sense"], job1.cplex["rows"], job1.cplex["cols"], job1.cplex["vals"])
# BB = B_and_B(eq)
# BB.solve_algorithem()