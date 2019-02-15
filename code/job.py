import csv
import cplex
from os import getpid
import time
import constraint_equations
import matplotlib.pyplot as plt
from job_operation import Operation
from job_resource import Resource
from branch_and_bound import B_and_B

class Job:

    def __init__(self, csv_path, cplex_solution=False):
        self.N = 1e4
        self.resources = {}
        self.operations = {}
        self.preferences = {}
        self.cplex = {'obj' : [], 'ub' : [], 'lb' : [], 'ctype' : "", 'colnames' : [], 'rhs' : [],
            'rownames' : [], 'sense' : "", 'rows' : [], 'cols' : [], 'vals' : []}
        self.x_names = []
        self.UB = 0
        self.cplex_solution = cplex_solution
        self.csv_problem(csv_path)


    def csv_problem(self, csv_path):
        """
        read from csv file the problem and initialize job attributes.
        create resources, operations and initialize the operations with modes
        return: None
        """
        # read csv file as dict
        with open(csv_path, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            # from every line take operation, mode, resource, start time, duration and preferences
            for row in csv_reader:
                # if the resource first seen, create it
                if row["resource"] not in self.resources:
                    self.resources[row["resource"]] = Resource(row["resource"])
                # if the operation first seen, create it
                if row["operation"] not in self.operations:
                    self.operations[row["operation"]] = Operation(row["operation"])
                # add mode to operation with all relevent data
                self.operations[row["operation"]].add_mode_to_operation(row["mode"], self.resources[row["resource"]], float(row["start"]), float(row["duration"]))
                # save the preferences for every operation
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

        self.__find_rtag_and_tim()
        self.__init_cplex_variable_parameters()
        self.__find_UB()
        self.__create_equations()


    def __find_rtag_and_tim(self):
        """
        set the r' and the Tim for all modes
        return: None
        """
        for op in self.operations.values():
            for mode in op.modes:
                mode.find_rtag()
                mode.find_tim()


    def __find_UB(self):
        """
        find the UB to the problem by sum all the max(Tim) of every operation
        return: None
        """
        for operation in self.operations.values():
            max_t_im = 0
            for mode in operation.modes:
                if mode.tim > max_t_im:
                    max_t_im = mode.tim
            self.UB += max_t_im


    def __init_cplex_variable_parameters(self):
        """
        initialize cplex dict according to the problem data.
        return: None
        """
        # add all Xi,m,r,l to colnames list
        for operation in self.operations.values():
            for mode in operation.modes:
                for resource in mode.needed_resources:
                    for index in range(1, resource.size + 1):
                        self.cplex["colnames"].append("X{},{},{},{}".format(operation.num_of_op, 
                            mode.num_mode, resource.number, index))

        self.x_names = self.cplex["colnames"][:]
        x_i_m_r_l_len = len(self.x_names)
        # add all Ti to colnames list
        for index in range(1, len(self.operations) + 1):
            self.cplex["colnames"].append("T" + str(index))

        # add all Tr,l to colnames list
        for resource in self.resources.values():
            for index in range(1, resource.size + 1):
                self.cplex["colnames"].append("T{},{}".format(resource.number, index))

        # add F to colnames list
        self.cplex["colnames"].append("F")

        # initialize ctype - b&b solution
        if self.cplex_solution:
            self.cplex["ctype"] = 'I' * x_i_m_r_l_len
            self.cplex["ctype"] += 'C' * (len(self.cplex["colnames"]) - x_i_m_r_l_len)
        else:
            self.cplex["ctype"] = 'C' * len(self.cplex["colnames"])

        # initialize lb
        self.cplex["lb"] = [0] * len(self.cplex["colnames"])

        # initialize ub - Ximrl ub is 1 and Ti, Tim and F ub is infinity
        self.cplex["ub"] = [1] * x_i_m_r_l_len
        self.cplex["ub"] += [cplex.infinity] * (len(self.cplex["colnames"]) - x_i_m_r_l_len)

        # initialize obj
        self.cplex["obj"] = [0] * (len(self.cplex["colnames"]) - 1)
        self.cplex["obj"].append(1)


    def __create_equations(self):
        """
        create all equations.
        return: None
        """
        constraint_equations.first_equations(self.operations, self.cplex)
        constraint_equations.second_equations(self.operations, self.cplex)
        constraint_equations.third_equations(self.resources, self.cplex)
        constraint_equations.fourth_equations(self.operations, self.preferences, self.cplex)
        constraint_equations.fifth_equations(self.resources, self.cplex)
        constraint_equations.sixth_equations(self.operations, self.N, self.cplex)
        constraint_equations.seventh_equations(self.operations, self.cplex)
        # constraint_equations.eighth_equations(self.resources, self.cplex)


    def draw_solution(self, choices, title):
        """
        collecting the data from the cplex solution
        choices: dict, parameters name : value
        title: string, solution time, number of nodes, queue size and max depth
        return: None
        """
        operations = {}
        choices_modes = []
        # for each operation collect which mode were selected, Tim and resources
        for operation_name, op in self.operations.items():
            mode_found = False
            operations[operation_name] = {}
            operations[operation_name]["resources"] = {}
            resources = None
            for name, val in choices.items():
                # if Xi,m,r,l set to 1 check him
                if name.startswith("X" + operation_name + ",") and val == 1:
                    # check if operation's mode already known 
                    if not mode_found:
                        # from the mode save it number, needed resources and duration of the mode
                        for mode in op.modes:
                            if name.startswith("X" + operation_name + "," + mode.num_mode):
                                operations[operation_name]["duration"] = mode.tim
                                resources = mode.needed_resources
                                choices_modes.append("operation " + operation_name + "\nmode " + str(mode.num_mode))
                                mode_found = True
                    # remove from Xi,m,r,l the X and split the rest by comma
                    i, m, r, l = name[1:].split(",")
                    # find the appropriate Tr,l for the Xi,m,r,l
                    resource_start_time = choices["T" + r + "," + l]
                    resource_duration = ""
                    # for each resource save it start time and duration
                    for resource in resources:
                        if resource.number == r:
                            resource_duration = resource.get_usage_duration(i,m)
                    operations[operation_name]["resources"][r] = {"start" : float(resource_start_time), "duration" : resource_duration}
                # save the start time of the operation
                if name == "T" + operation_name:
                    operations[operation_name]["start"] = val
        self.__draw_collected_data(operations, title, choices_modes)


    def __draw_collected_data(self, operations, title, choices_modes):
        """
        set the axis and draw the collected data
        operations: dict, has all data from cplex
        title: string, solution time, number of nodes, queue size and max depth
        choices_modes: list, for each operation which mode was chosen
        return: None
        """
        start_y = 0
        plt.figure(figsize=(25,10))
        plt.subplots_adjust(left=0.1, right=0.98, bottom=0.1, top=0.9)
        plt.title(title, fontsize=14)
        plt.ylabel('operation & modes', fontsize=16)
        plt.xlabel('time', fontsize=16)
        x_ticks = []
        for op in operations.values():
            div = len(op["resources"])
            x_ticks.append(op["start"])
            x_ticks.append(op["start"] + op["duration"])
            self.__drow_rectangle(start_y, start_y + 1, op)
            index = 0
            for resource_name, resource in op["resources"].items():
                self.__drow_rectangle(start_y + index / div, start_y + (index + 1) / div, resource, 1, "r" + resource_name)
                index += 1
            start_y += 1
        plt.xticks(list(set(x_ticks)))
        plt.yticks([0.5 + i for i in range(len(operations) + 1)], choices_modes)
        for i in range(len(operations) + 1):
            plt.axhline(i, color='black')
        plt.show()


    def __drow_rectangle(self, start_y, end_y, value, width=2, text=""):
        """
        draw rectangle.
        start_y: float, from where the rectangle start
        end_y: float, where the rectangle end
        value: dict, data for the x axis
        width: float, the width of the rectangle
        text: string, what to write in the rectangle
        return: None
        """
        y = [start_y, start_y, end_y, end_y, start_y]
        x = [value["start"], value["start"] + value["duration"],
             value["start"] + value["duration"], value["start"], value["start"]]
        plt.plot(x,y, linewidth=width)
        plt.text(value["start"] + 0.1, start_y + 0.03, text, fontsize=8)

if __name__ == '__main__':
    print("pid =", getpid())
    job1 = Job("problems\\Samaddar_Problem#16.csv", cplex_solution=False)
    print("|Xi,m,r,l| =", len(job1.x_names), "\n|equations| =", len(job1.cplex["rownames"]), "\nPrediction UB =", job1.UB)
    # input("press any key to continue\n")
    print("starting solve")
    start = time.time()
    BB = B_and_B(job1.cplex["obj"], job1.cplex["ub"], job1.cplex["lb"],
                job1.cplex["ctype"], job1.cplex["colnames"], job1.cplex["rhs"],
                job1.cplex["rownames"], job1.cplex["sense"], job1.cplex["rows"],
                job1.cplex["cols"], job1.cplex["vals"], job1.x_names, job1.UB, use_SP=True)
    choices, solution_data = BB.solve_algorithem()
    end = time.time()
    solution_data = "solution in %10f sec\n" % (end - start) + solution_data
    job1.draw_solution(choices, solution_data)
