import csv
import cplex
import os
import time
import equations
import matplotlib.pyplot as plt
from job_operation import Operation
from job_resource import Resource
from branch_and_bound import B_and_B

class Job:

    def __init__(self, csv_path):
        self.path = csv_path
        self.N = 1e4
        self.resources = {}
        self.operations = {}
        self.preferences = {}
        self.cplex = {'obj' : [], 'ub' : [], 'lb' : [], 'ctype' : "", 'colnames' : [], 'rhs' : [], 
                      'rownames' : [], 'sense' : "", 'rows' : [], 'cols' : [], 'vals' : []}
        self.x_names = []
        self.UB = 0
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
        self.__find_UB()
        self.create_equations()


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
                for resource in mode.needed_resources:
                    for index in range(1, resource.size + 1):
                        name = "X{},{},{},{}".format(operation.num_of_op, mode.num_mode, resource.number, index)
                        self.cplex["colnames"].append(name)

        self.x_names = self.cplex["colnames"][:]
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
        self.cplex["colnames"].append("F")

        # initialize ctype - b&b solution
        self.cplex["ctype"] = 'C' * len(self.cplex["colnames"])
        # self.cplex["ctype"] = 'I' * x_i_m_r_l_len
        # self.cplex["ctype"] += 'C' * (len(self.cplex["colnames"]) - x_i_m_r_l_len)

        # initialize lb
        self.cplex["lb"] = [0] * len(self.cplex["colnames"])

        # initialize ub - Ximrl ub is 1. Ti and Tim and C ub is infinity
        self.cplex["ub"] = [1] * x_i_m_r_l_len
        self.cplex["ub"] += [cplex.infinity] * (len(self.cplex["colnames"]) - x_i_m_r_l_len)

        # initialize obj
        self.cplex["obj"] = [0] * (len(self.cplex["colnames"]) - 1)
        self.cplex["obj"].append(1)


    def __find_UB(self):
        for operation in self.operations.values():
            max_t_im = 0
            for mode in operation.modes:
                if mode.tim > max_t_im:
                    max_t_im = mode.tim
            self.UB += max_t_im


    def create_equations(self):
        equations.first_equations(self.operations, self.cplex)
        equations.second_equations(self.operations, self.cplex)
        equations.third_equations(self.resources, self.cplex)
        equations.fourth_equations(self.operations, self.preferences, self.cplex)
        equations.fifth_equations(self.resources, self.cplex)
        equations.sixth_equations(self.operations, self.N, self.cplex)
        equations.seventh_equations(self.operations, self.cplex)


    def draw_solution(self, choices):
        operations = {}
        for operation_name, op in self.operations.items():
            mode_found = False
            operations[operation_name] = {}
            operations[operation_name]["resources"] = {}
            resources = None
            for name, T_time in choices.items():
                if name.startswith("X" + operation_name + ",") and T_time == 1:
                    if not mode_found:
                        for mode in op.modes:
                            if name.startswith("X" + operation_name + "," + mode.num_mode):
                                operations[operation_name]["duration"] = mode.tim
                                resources = mode.needed_resources
                                mode_found = True
                    i, m, r, l = name[1:].split(",")
                    resource_start_time = choices["T" + r + "," + l]
                    resource_duration = ""
                    for resource in resources:
                        if resource.number == r:
                            resource_duration = resource.get_usage_duration(i,m)
                    operations[operation_name]["resources"][r] = {"start" : float(resource_start_time), "duration" : resource_duration}
                if name == "T" + operation_name:
                    operations[operation_name]["start"] = T_time
        self.__draw_collected_data(operations)


    def __draw_collected_data(self, operations):
        start_y = 0
        plt.figure(figsize=(15,5))
        plt.subplots_adjust(left=0.04, right=0.99, bottom=0.08, top=0.95)
        plt.ylabel('operation')
        plt.xlabel('time')
        board = 0.02
        x_ticks = []
        for op in operations.values():
            div = len(op["resources"])
            self.__drow_rectangle(start_y, start_y + 1, op, x_ticks)
            index = 0
            for resource_name, resource in op["resources"].items():
                self.__drow_rectangle(start_y + index / div, start_y + (index + 1) / div, resource, x_ticks, 1, board, resource_name, "r")
                index += 1
            start_y += 1
        plt.xticks(list(set(x_ticks)))
        plt.yticks(range(len(operations) + 1))
        plt.show()


    def __drow_rectangle(self, start_y, end_y, value, x_ticks, width=2, board=0, key="", text=""):
        y = [start_y + board, start_y + board, end_y - board, end_y - board, start_y + board]
        # board *= 1.5
        x = [value["start"] + board, value["start"] + value["duration"] - board, 
             value["start"] + value["duration"] - board, value["start"] + board, value["start"] + board]
        x_ticks.append(value["start"])
        x_ticks.append(value["start"] + value["duration"])
        plt.plot(x,y, linewidth=width)
        plt.text(value["start"] + 0.1, start_y + 0.03, text + key, fontsize=8)


    def __str__(self):
        string = ""
        for key, value in self.operations.items():
            string += str(key) + " : { " + str(value) + " \n}\n"
        return string


print("pid =", os.getpid())
job1 = Job("data.csv")
print("|Xi,m,r,l| =", len(job1.x_names), "\n|equations| =", len(job1.cplex["rownames"]), "\nPrediction UB =", job1.UB)
input("press any key to continue\n")
print("starting solve")
start = time.time()
BB = B_and_B(job1.cplex["obj"], job1.cplex["ub"], job1.cplex["lb"],
             job1.cplex["ctype"], job1.cplex["colnames"], job1.cplex["rhs"],
             job1.cplex["rownames"], job1.cplex["sense"], job1.cplex["rows"],
             job1.cplex["cols"], job1.cplex["vals"], job1.x_names, job1.UB, False)
choices = BB.solve_algorithem()
end = time.time()
print("solution time is", end - start)
print(choices)
job1.draw_solution(choices)