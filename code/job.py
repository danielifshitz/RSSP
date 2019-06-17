from sqlite3 import connect
from cplex import infinity
import time
import copy
import constraint_equations
from job_operation import Operation
from job_resource import Resource
from graph import Graph
from genetic_algo import GA

class Job:

    def __init__(self, csv_path, cplex_solution=False, ub=None, sort_x=None, reverse=False):
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
            self.operations = self.__sort_operations_by_preferences(self.__sort_operations_by_pref, reverse)
            self.create_x_i_m_r_l()
        elif sort_x == "res":
            self.__sort_x_by_resources(reverse)
        else:
            self.create_x_i_m_r_l()
        self.__init_cplex_variable_parameters(cplex_solution)
        self.__create_equations()
        graph = self.create_bellman_ford_graph()
        self.LB = graph.bellman_ford_LB(0, len(self.operations) + 1)
        self.UBs = {}
        if ub == "greedy" or ub == "both":
            self.UBs["mode"] = self.__find_UB_greedy(self.__sort_operations_by_pref)
            self.UBs["operations"] = self.__find_UB_greedy_operations()
            self.UBs["preferences"] = self.__find_UB_greedy(self.__sort_operations_by_pref_len, reverse=True)
            self.UBs["preferences_mode"] = self.__find_UB_greedy_operations(less_modes=True)
        if ub == "ga" or ub == "both":
            ga = GA()
            self.UBs["ga_1"] = ga.solve(self)
            self.UBs["ga_2"] = ga.solve(self)
            self.UBs["ga_3"] = ga.solve(self)
            self.UBs["ga_4"] = ga.solve(self)
        self.UB = float("inf")
        for solution in self.UBs.values():
            self.UB = min(self.UB, solution["value"])


    def next_operations(self, choices):
        """
        according the given chose operations, collect all available operation by preferences.
        choices: string[], name of operations that already made/selected
        return: string[], all the available operation
        """
        next_ops = []
        for op_name, preferences in self.preferences.items():
            # dont take operations that already be selected
            if op_name not in choices:
                # for each operation check if all its preference operations in choices list, if so, save the operation
                if not [preference.number for preference in preferences if preference.number not in choices]:
                    next_ops.append(op_name)

        return next_ops


    def sort_resources(self):
        operations = {operation: self.__sort_operations_by_pref(self.preferences[operation]) for operation in self.operations}
        max_dependence = max(operations.values()) + 1
        res = {resource: [0] * max_dependence for resource in self.resources.keys()}
        for op_name, dependence in operations.items():
            operation = self.operations[op_name]
            for resource in operation.all_resources.keys():
                cell = res[resource.number]
                cell[dependence] += 1
        return res, max_dependence


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


    def __sort_operations_by_preferences(self, sort_function, reverse=False):
        """
        create operation dictionary that sort by the length of the preferences that each operation have.
        the length of the preferences is defined as the max number of following operation that need to be done
            to arrive to this operation.
        sort_function: function, __sort_operations_by_pref or __sort_operations_by_pref_len
        reverse: boolean, used only with __sort_operations_by_pref
        return: dictionary of operaions
        """
        # create a list that contains all operations number and sorted by there preferences length
        op_order = sorted(self.operations, key=lambda op: sort_function(op), reverse=reverse)
        operations = {}
        # create dictionary of [operation number: operation object]
        for op in op_order:
            operations[op] = self.operations[op]
        return operations


    def __sort_operations_by_pref_len(self, op):
        """
        a recursive funcion that calculate the max number of operation that came after given operation
        op: string, operation name
        return: the max len of the operation that need this opearion
        """
        preferences_len = [0]
        # check every operation
        for operation, preferences in self.preferences.items():
            # if operation have the given operation in it's preferences
            if self.operations[op] in preferences:
                # check the len of the operation and add 1 to the len
                preferences_len.append(self.__sort_operations_by_pref_len(operation) + 1)

        return max(preferences_len)


    def __sort_operations_by_pref(self, op):
        return self.__sort_operations_by_pref_recursive(self.preferences[op])


    def __sort_operations_by_pref_recursive(self, op_list):
        """
        a recursive funcion that calculate the max number of operation that need to be pass to arrive
            to operation with out preferences operations.
        op_list: operation[], list of preferences operations that need to be checked
        return: number, the langth from operation with out preferences operations
        """
        if not op_list:
            return 0

        return max([self.__sort_operations_by_pref_recursive(self.preferences[op.number]) for op in op_list]) + 1


    def get_min_start_time(self, mode_resorces_time, mode, index, op_mode):
        start_time = float("inf")
        resource_numbers = []
        for resource in mode.resources:
            if index[int(resource.number) -1] < len(mode_resorces_time[resource.number]) - 1:
                if mode_resorces_time[resource.number][index[int(resource.number) -1]]["end"] < start_time:
                    usage = resource.usage[op_mode]
                    start_time = mode_resorces_time[resource.number][index[int(resource.number) -1]]["end"] - usage["start_time"]
                    resource_numbers = [resource.number]
                elif mode_resorces_time[resource.number][index[int(resource.number) -1]]["end"] == start_time:
                    resource_numbers.append(resource.number)

        for resource_number in resource_numbers:
            index[int(resource_number) -1] += 1

        return start_time


    def add_mode_cross_resources(self, start_time, mode_resorces_time, mode, op_mode):
        index = [0] * len(mode_resorces_time)
        # skip all not relevent options - by preferences
        for resource in mode.resources:
            while mode_resorces_time[resource.number][index[int(resource.number) -1]]["end"] <= start_time:
                index[int(resource.number) -1] += 1

        while True:
            found = True
            for resource in mode.resources:
                if index[int(resource.number) -1] < len(mode_resorces_time[resource.number]) - 1:
                    resource_usage = resource.usage[op_mode]
                    current_usage = mode_resorces_time[resource.number][index[int(resource.number) -1]]
                    next_usage = mode_resorces_time[resource.number][index[int(resource.number) -1] + 1]
                    if len(mode_resorces_time[resource.number]) > 2 and start_time < current_usage["start"]:
                        search_index = 2
                        pre_usage = mode_resorces_time[resource.number][index[int(resource.number) -1] - 1]
                        while pre_usage["start"] > start_time and index[int(resource.number) -1] - search_index >= 0:
                            pre_usage = mode_resorces_time[resource.number][index[int(resource.number) -1] - search_index]
                            search_index += 1

                        found = start_time + resource_usage["start_time"] + resource_usage["duration"] <= pre_usage["end"]

                    if found and start_time + resource_usage["start_time"] < current_usage["end"]:
                        found = start_time + resource_usage["start_time"] + resource_usage["duration"] <= current_usage["start"]

                    if found:
                        search_index = 2
                        while next_usage["end"] < start_time + resource_usage["start_time"]:
                            next_usage = mode_resorces_time[resource.number][index[int(resource.number) -1] + search_index]
                            search_index += 1

                        found = next_usage["start"] >= start_time + resource_usage["start_time"] + resource_usage["duration"]

                    if not found:
                        break

            if found:
                return start_time

            start_time = max(0, self.get_min_start_time(mode_resorces_time, mode, index, op_mode))


    def add_mode(self, start_time, mode_resorces_time, mode, op_mode):
        for resource in mode.resources:
            usage = resource.usage[op_mode]
            # if resource start time in the mode != 0, it's meean that the reaource need only after that time
            if len(mode_resorces_time[resource.number]) != 1:
                start_time = max(start_time, mode_resorces_time[resource.number][-2]["end"] - usage["start_time"])

        return start_time


    def calc_adding_mode(self, pre_dur, mode_resorces_time, mode):
        """
        calculate the resources end time according to the selected operations before.
        pre_dur: numbers[], each cell contains preference operations end time.
        mode_resorces_time: dictionary, end time of each resource.
        mode: Mode, the mode that want to calculate.
        return: number - the end time of the mode, dictionary - the end time of every resource
        """
        op_mode = "{},{}".format(mode.op_number, mode.mode_number)
        # add the end time of each resource to the list of end time of the preferences
        pre_dur.append(self.add_mode_cross_resources(max(pre_dur), mode_resorces_time, mode, op_mode))
        # take the biggest end time to start the mode
        mode_start_time = max(pre_dur)
        # for each resource in mode, add it start time + duration to the mode start time
        for resource in mode.resources:
            usage = resource.usage[op_mode]
            mode_resorces_time[resource.number].append({"start": mode_start_time + usage["start_time"], "end": mode_start_time + usage["duration"] + usage["start_time"]})
            mode_resorces_time[resource.number] = sorted(mode_resorces_time[resource.number], key=lambda usage: usage["start"])

        return mode_start_time + mode.tim, mode_resorces_time


    def calc_adding_operations(self, operations, op_end_times, resorces_time, selected_mode=None):
        min_time_mode = float("inf")
        for name, operation in operations.items():
            pre_dur = [0]
            for pre in self.preferences[name]:
                pre_dur.append(op_end_times[pre.number])

            if selected_mode:
                for mode in operation.modes:
                    if mode.mode_number == selected_mode:
                        modes = [mode]
                        break

            else:
                modes = operation.modes

            for mode in modes:
                mode_time, mode_resorces_time = self.calc_adding_mode(pre_dur[:], copy.deepcopy(resorces_time), mode)
                if min_time_mode > mode_time:
                    best_resorces_time = mode_resorces_time
                    min_time_mode = mode_time
                    choisen_operation = mode.op_number

        return best_resorces_time, min_time_mode, choisen_operation


    def __find_UB_greedy(self, sort_function, reverse=False):
        start = time.time()
        op_end_times = {}
        resorces_time = {}
        for resorce in self.resources.keys():
            resorces_time[resorce] = [{"start": float("inf"), "end": float("inf")}]

        ub = 0
        for name, operation in self.__sort_operations_by_preferences(sort_function, reverse=reverse).items():
            resorces_time, min_time_mode, choisen_operation = self.calc_adding_operations({name: operation}, op_end_times, resorces_time.copy())
            ub = max(ub, min_time_mode)
            op_end_times[choisen_operation] = min_time_mode

        run_time = time.time() - start
        return {"value": ub, "time": run_time}


    def __find_UB_greedy_operations(self, less_modes=False):
        start = time.time()
        op_end_times = {}
        resorces_time = {}
        for resorce in self.resources.keys():
            resorces_time[resorce] = [{"start": float("inf"), "end": float("inf")}]

        ub = 0
        operations = self.next_operations([])
        while operations:
            operations = {op: self.operations[op] for op in operations}
            if less_modes:
                operations = min(operations.values(), key=lambda operation: len(operation.modes))
                operations = {operations.number: operations}
            resorces_time, min_time_mode, choisen_operation = self.calc_adding_operations(operations, op_end_times, resorces_time.copy())
            ub = max(ub, min_time_mode)
            op_end_times[choisen_operation] = min_time_mode
            operations = self.next_operations(op_end_times.keys())

        run_time = time.time() - start
        return {"value": ub, "time": run_time}


    def find_UB_ga(self, operations_order, selected_modes):
        start = time.time()
        op_end_times = {}
        resorces_time = {}
        for resorce in self.resources.keys():
            resorces_time[resorce] = [{"start": float("inf"), "end": float("inf")}]

        ub = 0
        for op_name in operations_order:
            operation = self.operations[op_name]
            resorces_time, min_time_mode, choisen_operation = self.calc_adding_operations({op_name: operation}, op_end_times, resorces_time.copy(), str(selected_modes[int(op_name) - 1]))
            ub = max(ub, min_time_mode)
            op_end_times[choisen_operation] = min_time_mode

        run_time = time.time() - start
        return {"value": ub, "time": run_time}


    def create_bellman_ford_graph(self):
        graph = Graph(len(self.operations) + 2)
        for op in self.__sort_operations_by_preferences(self.__sort_operations_by_pref).keys():
            for pre_op in self.preferences[op]:
                graph.addEdge(int(pre_op.number), int(op), pre_op.get_min_tim())

            graph.addEdge(0, int(op), 0)
            graph.addEdge(int(op), len(self.operations) + 1, self.operations[op].get_min_tim())

        return graph


    def __sort_x_by_resources(self, reverse=False):
        """
        create and sort the Xi,m,r,l according to the usage resources for the cplex equations.
        reverse: boolean, True - sort from the most usage resources,
            False - sort from the lass usage resources
        retrun None
        """
        res_order = sorted(self.resources.values(), key=lambda resource: resource.size, reverse=reverse)
        for resource in res_order:
            for op_mode in resource.usage.keys():
                for index in range(1, resource.size + 1):
                    self.cplex["colnames"].append("X{},{},{}".format(op_mode, resource.number, index))


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
