from sqlite3 import connect
from cplex import infinity
import constraint_equations
from job_operation import Operation
from job_resource import Resource

class Job:

    def __init__(self, csv_path, cplex_solution=False, sort_x=None, reverse=False):
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
        if sort_x == "pre":
            self.operations = self.__sort_x_by_preferences(reverse)
            self.create_x_i_m_r_l()
        elif sort_x == "res":
            self.__sort_x_by_resources(reverse)
        else:
            self.create_x_i_m_r_l()
        self.__init_cplex_variable_parameters(cplex_solution)
        self.UB = self.__find_UB_greedy()
        self.__create_equations()


    def sql_problem(self, problem_ID):
        """
        read problrm data from the DB using sql querys and initialize all class parameters.
        the DB contains 2 tables with problem data:
            * OpMoRe: the start time and the duration of resource use by operation in some mode.
            * Priority: operations and there preferences operations
        from each table we take the relevant data by using the problem_ID.
        problem_ID: number, the wanted problem number to be sulved
        return: None
        """
        OPERATION = 0
        MODE = 1
        RESOURCE = 2
        START = 3
        DURATION = 4
        PRE_OP = 1
        conn = connect('data.db')
        c = conn.cursor()
        c.execute("SELECT Oper_ID, Mode_ID, Res_ID, Ts,(Tf - Ts) AS DUR FROM OpMoRe where Problem_ID = {0} ORDER BY Oper_ID, Mode_ID, Res_ID".format(problem_ID))
        query = c.fetchall()
        # from every line take operation,mode, resources and times
        for row in query:
            operation = str(row[OPERATION])
            resource = str(row[RESOURCE])
            mode = str(row[MODE])
            # if the resource first seen, create it
            if resource not in self.resources:
                self.resources[resource] = Resource(resource)
            # if the operation first seen, create it and add it into preferences dictionary
            if operation not in self.operations:
                self.operations[operation] = Operation(operation)
                self.preferences[operation] = []
            # add mode to operation with all relevent data
            self.operations[operation].add_mode(mode, self.resources[resource], row[START], row[DURATION])

        c.execute("SELECT Suc_Oper_ID, Pre_Oper_ID FROM Priority where Problem_ID = {0} ORDER BY Suc_Oper_ID, Pre_Oper_ID".format(problem_ID))
        query = c.fetchall()
        # from every line take operation and preferences
        for row in query:
            if row[PRE_OP]:
                operation = str(row[OPERATION])
                pre_op = str(row[PRE_OP])
                # add preference operation (Operation object) to the preferences dictionary
                self.preferences[operation].append(self.operations[pre_op])

        conn.close()


    def __find_rtag_and_tim(self):
        """
        set the r' and the Tim for all modes
        return: None
        """
        for op in self.operations.values():
            for mode in op.modes:
                mode.find_rtag()
                mode.find_tim()


    def __sort_x_by_preferences(self, reverse=False):
        """
        create operation dictionary that sort by the length of the preferences that each operation have.
        the length of the preferences is defined as the max number of following operation that need to be done
            to arrive to this operation.
        return: dictionary of operaions
        """
        # create a list that contains all operations number and sorted by there preferences length
        op_order = sorted(self.operations, key=lambda op: self.__sort_x_by_pref(self.preferences[op]), reverse=reverse)
        operations = {}
        # create dictionary of [operation number: operation object]
        for op in op_order:
            operations[op] = self.operations[op]
        return operations


    def __sort_x_by_pref(self, op_list):
        """
        a recursive funcion that calculate the max number of operation that need to be pass to arrive
            to operation with out preferences operations.
        op_list: list of preferences operations that need to be checked
        return: number, the langth from operation with out preferences operations
        """
        if not op_list:
            return 0

        return max([self.__sort_x_by_pref(self.preferences[op.number]) for op in op_list]) + 1


    def __sort_x_by_resources(self, reverse=False):
        res_order = sorted(self.resources.values(), key=lambda resource: resource.size, reverse=reverse)
        for resource in res_order:
            for op_mode in resource.usage.keys():
                for index in range(1, resource.size + 1):
                    self.cplex["colnames"].append("X{},{},{}".format(op_mode, resource.number, index))


    def __find_UB_greedy(self):
        op_end_times = {}
        resorce_time = {}
        for resorce in self.resources.keys():
            resorce_time[resorce] = 0
        ub = 0
        for name, operation in self.__sort_x_by_preferences().items():
            pre_dur = []
            for pre in self.preferences[name]:
                pre_dur.append(op_end_times[pre.number])
            min_time_mode = float("inf")
            op_resorce_time = resorce_time.copy()
            for mode in operation.modes:
                max_dur = pre_dur[:]
                mode_resorce_time = resorce_time.copy()
                op_mode = "{},{}".format(name, mode.mode_number)
                for resource in mode.resources:
                    usage = resource.usage[op_mode]
                    max_dur.append(mode_resorce_time[resource.number] - usage["start_time"])
                start = max(max_dur)
                for resource in mode.resources:
                    usage = resource.usage[op_mode]
                    mode_resorce_time[resource.number] += usage["start_time"] + usage["duration"]
                if min_time_mode > start + mode.tim:
                    op_resorce_time = mode_resorce_time
                    min_time_mode = start + mode.tim
            ub = max(ub, min_time_mode)
            resorce_time = op_resorce_time
            op_end_times[name] = min_time_mode
        return ub


    def create_x_i_m_r_l(self):
        # add all Xi,m,r,l to colnames list
        for operation in self.operations.values():
            for mode in operation.modes:
                for resource in mode.resources:
                    for index in range(1, resource.size + 1):
                        self.cplex["colnames"].append("X{},{},{},{}".format(operation.number,
                            mode.mode_number, resource.number, index))


    def __init_cplex_variable_parameters(self, cplex_solution):
        """
        initialize cplex dictionary according to the problem data.
        return: None
        """
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
