import csv
import sqlite3
from cplex import infinity
import constraint_equations
from job_operation import Operation
from job_resource import Resource

class Job:

    def __init__(self, csv_path, cplex_solution=False, sort_x=False):
        self.N = 1e4
        self.resources = {}
        self.operations = {}
        self.preferences = {}
        self.cplex = {'obj' : [], 'ub' : [], 'lb' : [], 'ctype' : "", 'colnames' : [], 'rhs' : [],
            'rownames' : [], 'sense' : "", 'rows' : [], 'cols' : [], 'vals' : []}
        self.x_names = []
        self.UB = 0
        self.sql_problem(csv_path)
        self.__find_rtag_and_tim()
        if sort_x:
            self.__sort_x_by_preferences()
        self.__init_cplex_variable_parameters(cplex_solution)
        self.__find_UB()
        self.__create_equations()


    def sql_problem(self, problem_ID):
        """

        return: None
        """
        #
        OPERATION = 0
        MODE = 1
        RESOURCE = 2
        START = 3
        DURATION = 4
        PRE_OP = 1
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("SELECT Oper_ID, Mode_ID, Res_ID, Ts,(Tf - Ts) AS DUR FROM OpMoRe where Problem_ID = {0} ORDER BY Oper_ID, Mode_ID, Res_ID".format(problem_ID))
        query = c.fetchall()
        # from every line take operation,mode, resources and times
        for row in query:
            # if the resource first seen, create it
            if str(row[RESOURCE]) not in self.resources:
                self.resources[str(row[RESOURCE])] = Resource(str(row[RESOURCE]))
            # if the operation first seen, create it and add it into preferences dictionary
            if str(row[OPERATION]) not in self.operations:
                self.operations[str(row[OPERATION])] = Operation(str(row[OPERATION]))
                self.preferences[str(row[OPERATION])] = []
            # add mode to operation with all relevent data
            self.operations[str(row[OPERATION])].add_mode(str(row[MODE]), self.resources[str(row[RESOURCE])], row[START], row[DURATION])

        c.execute("SELECT Suc_Oper_ID, Pre_Oper_ID FROM Priority where Problem_ID = {0} ORDER BY Suc_Oper_ID, Pre_Oper_ID".format(problem_ID))
        query = c.fetchall()
        # from every line take operation and preferences
        for row in query:
            if row[PRE_OP]:
                # add preference operation (Operation object) to the preferences dictionary
                self.preferences[str(row[OPERATION])].append(self.operations[str(row[PRE_OP])])


    def csv_problem(self, csv_path):
        """
        read from csv file the problem and initialize job attributes.
        create resources, operations and initialize the operations with modes
        return: None
        """
        # read csv file as dictionary
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
                self.operations[row["operation"]].add_mode(row["mode"], self.resources[row["resource"]], float(row["start"]), float(row["duration"]))
                # save the preferences for every operation
                for op in row["preferences"].split(";"):
                    if op:
                        if row["operation"] in self.preferences:
                            self.preferences[row["operation"]].append(self.operations[op])
                        else:
                            self.preferences[row["operation"]] = [self.operations[op]]
                    else:
                        self.preferences[row["operation"]] = []

            for op, preferences in self.preferences.items():
                if preferences:
                    self.preferences[op] = list(set(preferences))


    def __find_rtag_and_tim(self):
        """
        set the r' and the Tim for all modes
        return: None
        """
        for op in self.operations.values():
            for mode in op.modes:
                mode.find_rtag()
                mode.find_tim()


    def __sort_x_by_preferences(self):
        op_order = sorted(self.operations, key=lambda op: self.__sort_x_by_pref(self.preferences[op]))
        operations = {}
        for op in op_order:
            operations[op] = self.operations[op]
        self.operations = operations


    def __sort_x_by_pref(self, op_list):
        if not op_list:
            return 0

        return max([self.__sort_x_by_pref(self.preferences[op.number]) for op in op_list]) + 1


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


    def __init_cplex_variable_parameters(self, cplex_solution):
        """
        initialize cplex dictionary according to the problem data.
        return: None
        """
        # add all Xi,m,r,l to colnames list
        for operation in self.operations.values():
            for mode in operation.modes:
                for resource in mode.resources:
                    for index in range(1, resource.size + 1):
                        self.cplex["colnames"].append("X{},{},{},{}".format(operation.number,
                            mode.mode_number, resource.number, index))

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
        if cplex_solution:
            self.cplex["ctype"] = 'I' * x_i_m_r_l_len
            self.cplex["ctype"] += 'C' * (len(self.cplex["colnames"]) - x_i_m_r_l_len)
        else:
            self.cplex["ctype"] = 'C' * len(self.cplex["colnames"])

        # initialize lb
        self.cplex["lb"] = [0] * len(self.cplex["colnames"])

        # initialize ub - Ximrl ub is 1 and Ti, Tim and F ub is infinity
        self.cplex["ub"] = [1] * x_i_m_r_l_len
        self.cplex["ub"] += [infinity] * (len(self.cplex["colnames"]) - x_i_m_r_l_len)

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
