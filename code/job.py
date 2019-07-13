from sqlite3 import connect
from cplex import infinity
import time
import copy
import constraint_equations
from job_operation import Operation
from job_resource import Resource
from bellman_ford import Bellman_Ford
from genetic_algo import GA

class Job:

    """
    this class read problems from the database, calculate the UB and LB and create equations.
    """

    def __init__(self, problem_id, cplex_solution=False, ub=None, sort_x=None, reverse=False, repeate=1):
        self.N = 1e4
        self.resources = {}
        self.operations = {}
        self.preferences = {}
        self.cplex = {'obj' : [], 'ub' : [], 'lb' : [], 'ctype' : "", 'colnames' : [], 'rhs' : [],
            'rownames' : [], 'sense' : "", 'rows' : [], 'cols' : [], 'vals' : []}
        self.x_names = []
        self.UB = 0
        self.sql_problem(problem_id, repeate)
        # for each operation save the preferences len to start, used in recursive functions
        self.operations_preferences_position = [-1] * len(self.operations)
        self.__find_rtag_and_tim()
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
        self.draw_UB = None
        for solution in self.UBs.values():
            if solution["value"] < self.UB:
                self.UB = solution["value"]
                self.draw_UB = solution["to_draw"]

        # if the LB = UB we not to create equations
        if self.UB != self.LB:
            if sort_x == "pre":
                self.operations = self.__sort_operations_by_preferences(self.__sort_operations_by_pref, reverse)
                self.create_x_i_m_r_l()
            elif sort_x == "res":
                self.__sort_x_by_resources(reverse)
            else:
                self.create_x_i_m_r_l()
            self.__init_cplex_variable_parameters(cplex_solution)
            self.__create_equations()


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


    def read_OpMoRe_query(self, query, repeate):
        """
        take data from OpMoRe query and initialize all class parameters.
        query: dictionary, the OpMoRe query
        repeate: number, number of times to duplicate the problem
        return: None
        """
        OPERATION = 0
        MODE = 1
        RESOURCE = 2
        START = 3
        DURATION = 4
        operations_added = 0 # use to save the number of operations that were created in the last repeate 
        for _ in range(repeate):
            # from every line take operation,mode, resources and times
            for row in query:
                operation = str(operations_added + row[OPERATION])
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
            operations_added = len(self.operations)


    def get_rearguard_operations(self, operations_in_cycle):
        """
        find and return all operations that no one need them as preferences operations
        operations_in_cycle: number of operations in cycle (operation length / repeate)
        return: list, rearguard operations
        """
        rearguard_operations = [0] * operations_in_cycle
        for pre_list in self.preferences.values():
            for pre_op in pre_list:
                rearguard_operations[int(pre_op.number) - 1] += 1
        return [index+1 for index, op in enumerate(rearguard_operations) if op == 0]


    def read_Priority_query(self, query, repeate):
        """
        take data from Priority query and initialize preferences dictionary.
        query: dictionary, the Priority query
        repeate: number, number of times to duplicate the problem
        return: None
        """
        OPERATION = 0
        PRE_OP = 1
        operations_in_cycle = int(len(self.operations) / repeate)
        for loop in range(repeate):
            # from every line take operation and preferences
            for row in query:
                # if row[PRE_OP]:
                operation = str(operations_in_cycle * loop + row[OPERATION])
                pre_op = str(operations_in_cycle * loop + row[PRE_OP])
                # add preference operation (Operation object) to the preferences dictionary
                self.preferences[operation].append(self.operations[pre_op])

            if loop == 0:
                rearguard_operations = self.get_rearguard_operations(operations_in_cycle)

            else:
                # form repeate 2 to n, every operation that hasn't preferences, use last rearguard operations as her preferences operations
                for operation_number in range(loop * operations_in_cycle + 1, (loop + 1) * operations_in_cycle + 1):
                    if not self.preferences[str(operation_number)]:
                        for pre_op in rearguard_operations:
                            self.preferences[str(operation_number)].append(self.operations[str(operations_in_cycle * (loop - 1) + pre_op)])


    def sql_problem(self, problem_ID, repeate):
        """
        read problrm data from the DB using sql querys and initialize all class parameters.
        the DB contains 2 tables with problem data:
            * OpMoRe: the start time and the duration of resource use by operation in some mode.
            * Priority: operations and there preferences operations
        from each table we take the relevant data by using the problem_ID.
        problem_ID: number, the wanted problem number to be sulved
        repeate: number, number of times to duplicate the problem
        return: None
        """
        conn = connect('data.db')
        c = conn.cursor()
        c.execute("SELECT Oper_ID, Mode_ID, Res_ID, Ts,(Tf - Ts) AS DUR FROM OpMoRe where Problem_ID = {0} ORDER BY Oper_ID, Mode_ID, Res_ID".format(problem_ID))
        query = c.fetchall()
        self.read_OpMoRe_query(query, repeate)

        c.execute("SELECT Suc_Oper_ID, Pre_Oper_ID FROM Priority where Problem_ID = {0} ORDER BY Suc_Oper_ID, Pre_Oper_ID".format(problem_ID))
        query = c.fetchall()
        self.read_Priority_query(query, repeate)
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
        operations_preferences_len = [-1] * len(self.operations)
        op_order = sorted(self.operations, key=lambda op: sort_function(op, operations_preferences_len), reverse=reverse)
        operations = {}
        # create dictionary of [operation number: operation object]
        for op in op_order:
            operations[op] = self.operations[op]
        return operations


    def __sort_operations_by_pref_len(self, op, operations_preferences_len):
        """
        a recursive funcion that calculate the max number of operation that came after the given operation
        op: string, operation name
        operations_preferences_len: list, save the len for each operation to save not needed calculations
        return: number, the max len of the operation that need this opearion
        """
        if operations_preferences_len[str(op)] == -1:
            preferences_len = [0]
            # check every operation
            for operation, preferences in self.preferences.items():
                # if operation have the given operation in it's preferences
                if self.operations[op] in preferences:
                    # check the len of the operation and add 1 to the len
                    preferences_len.append(self.__sort_operations_by_pref_len(operation, operations_preferences_len) + 1)

            operations_preferences_len[str(op)] = max(preferences_len)
        return operations_preferences_len[str(op)]


    def __sort_operations_by_pref(self, op):
        """
        call to __sort_operations_by_pref_recursive with all preferences operations
        op: string, operation name
        return: number
        """
        if self.operations_preferences_position[int(op) - 1] == -1:
            self.operations_preferences_position[int(op) - 1] = self.__sort_operations_by_pref_recursive(self.preferences[op])
        return self.operations_preferences_position[int(op) - 1]


    def __sort_operations_by_pref_recursive(self, op_list):
        """
        a recursive funcion that calculate the max number of operation that need to be pass to arrive
            to operation without preferences operations.
        op_list: operation[], list of preferences operations that need to be checked
        return: number, the length from operation without preferences operations
        """
        if not op_list:
            return 0

        distance = 0
        for op in op_list:
            if self.operations_preferences_position[int(op.number) - 1] == -1:
                distance = max(distance, self.__sort_operations_by_pref_recursive(self.preferences[op.number]))
            else:
                distance = max(distance, self.operations_preferences_position[int(op.number) - 1])

        return distance + 1
        # return max([self.__sort_operations_by_pref_recursive(self.preferences[op.number]) for op in op_list]) + 1


    def get_min_start_time(self, mode_resorces_time, mode, index, op_mode):
        """
        add all mode's resources and calcolate the finish time.
        mode_resorces_time: dictionary, the resources usage time
        mode: Mode, mode object
        index: list of numbers, the number of times that each resource been used
        op_mode: string, "operatin_mode" string
        return: minimom start time for this mode
        """
        start_time = float("inf")
        resource_numbers = []
        for resource in mode.resources:
            # if number of usage less then the last usage
            if index[int(resource.number) -1] < len(mode_resorces_time[resource.number]) - 1:
                if mode_resorces_time[resource.number][index[int(resource.number) -1]]["end"] < start_time:
                    usage = resource.usage[op_mode]
                    start_time = mode_resorces_time[resource.number][index[int(resource.number) -1]]["end"] - usage["start_time"]
                    resource_numbers = [resource.number]
                elif mode_resorces_time[resource.number][index[int(resource.number) -1]]["end"] == start_time:
                    resource_numbers.append(resource.number)

        # add 1 to all usage resources
        for resource_number in resource_numbers:
            index[int(resource_number) -1] += 1

        return start_time


    def add_mode_cross_resources(self, start_time, mode_resorces_time, mode, op_mode):
        """
        try add mode with cross resources if neseraly.
        start_time: minimom start time, according to the preferences
        mode_resorces_time: dictionary, the resources usage time
        mode: Mode, mode object
        op_mode: string, "operatin_mode" string
        """
        index = [0] * len(mode_resorces_time)
        # skip all not relevent options - by preferences
        for resource in mode.resources:
            while mode_resorces_time[resource.number][index[int(resource.number) -1]]["end"] <= start_time:
                index[int(resource.number) -1] += 1

        while True:
            found = True
            # check all resources
            for resource in mode.resources:
                # check if the index less the number of resource usage
                # if not, this usage will be added at the end of the resource time
                if index[int(resource.number) -1] < len(mode_resorces_time[resource.number]) - 1:
                    # resource usage data, from the Resource object
                    resource_usage = resource.usage[op_mode]
                    current_usage = mode_resorces_time[resource.number][index[int(resource.number) -1]]
                    next_usage = mode_resorces_time[resource.number][index[int(resource.number) -1] + 1]
                    # if the usage starts before the index usage
                    if len(mode_resorces_time[resource.number]) > 2 and start_time < current_usage["start"]:
                        search_index = 2
                        pre_usage = mode_resorces_time[resource.number][index[int(resource.number) -1] - 1]
                        while pre_usage["start"] > start_time and index[int(resource.number) -1] - search_index >= 0:
                            pre_usage = mode_resorces_time[resource.number][index[int(resource.number) -1] - search_index]
                            search_index += 1

                        found = start_time + resource_usage["start_time"] + resource_usage["duration"] <= pre_usage["end"]

                    # if the usage drops on the last usage
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
            # if all resources was placed, return the start time
            if found:
                return start_time

            start_time = max(0, self.get_min_start_time(mode_resorces_time, mode, index, op_mode))


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
        """
        add operation with the best mode.
        operations: list of Operation, part of job operations
        op_end_times: dictionary, the end time of each operation
        resorces_time: dictionary, resources end time
        selected_mode: number, if we want to select spesific mode
        return: dictionary
        """
        min_time_mode = float("inf")
        for name, operation in operations.items():
            pre_dur = [0]
            # save all preferences operation end time
            for pre in self.preferences[name]:
                pre_dur.append(op_end_times[pre.number]["end_time"])

            if selected_mode:
                # modes = [mode for mode in operation.modes if mode.mode_number == selected_mode]
                for mode in operation.modes:
                    if mode.mode_number == selected_mode:
                        modes = [mode]
                        break

            else:
                modes = operation.modes

            # check all modes and take the best
            for mode in modes:
                mode_time, mode_resorces_time = self.calc_adding_mode(pre_dur[:], copy.deepcopy(resorces_time), mode)
                if min_time_mode > mode_time:
                    best_resorces_time = mode_resorces_time
                    min_time_mode = mode_time
                    choisen_operation = mode.op_number
                    best_mode = mode

        return best_resorces_time, min_time_mode, choisen_operation, best_mode


    def init_operations_UB_to_draw(self, op_end_times, solution_data):
        """
        creat dictionary with all data to draw the solution, this dictionary contains:
            mode: the selected mode number for each operation
            start: operation start time
            duration: operation duration
            resources: for each operation we save in dictionary {"start" : resource global start time, "duration" : resource duration}
        with this data we can draw the solution if the UB = LB
        op_end_times: dictionary, for each operation  we save {"mode": Mode object, "end_time": operation global end time }
        solution_data: string with solution data: time, number of nodes and queue size
        return dictionary {"operations": dictionary, "title": string, "choices_modes": list of strings}
        """
        operations = {}
        choices_modes = []
        for operation_name, operation_data in op_end_times.items():
            operations[operation_name] = {"resources": {}}
            mode = operation_data["mode"]
            # save the string which show the selected mode for each operation
            choices_modes.append("operation " + operation_name + "\nmode " + str(mode.mode_number))
            operation_start_time = operation_data["end_time"] - mode.tim
            # operation start time
            operations[operation_name]["start"] = operation_start_time
            # operation duration
            operations[operation_name]["duration"] = mode.tim
            # for each operation save resources data
            for resource in mode.resources:
                resource_duration = resource.get_usage_duration(operation_name, mode.mode_number)
                resource_start_time = resource.get_usage_start_time(operation_name, mode.mode_number)
                # save the start time and the usage duration of the resource
                operations[operation_name]["resources"][resource.number] = {"start" : operation_start_time + resource_start_time, "duration" : resource_duration}

        return {"operations": operations, "title": solution_data, "choices_modes": choices_modes}


    def __find_UB_greedy(self, sort_function, reverse=False):
        """
        find UB using greedy function.
        sort_function: function, the function that return the operations order
        reverse: boolean, send to the sort_function
        return dictionary, found UB , how much time its took and draw data
        """
        start = time.time()
        op_end_times = {}
        resorces_time = {}
        for resorce in self.resources.keys():
            resorces_time[resorce] = [{"start": float("inf"), "end": float("inf")}]

        ub = 0
        for name, operation in self.__sort_operations_by_preferences(sort_function, reverse=reverse).items():
            resorces_time, min_time_mode, choisen_operation, best_mode = self.calc_adding_operations({name: operation}, op_end_times, resorces_time.copy())
            ub = max(ub, min_time_mode)
            op_end_times[choisen_operation] = {"mode": best_mode, "end_time": min_time_mode}

        run_time = time.time() - start
        solution_data = "solution in {:.10f} sec\ncreated nodes = 0, max queue size = 0".format(run_time)
        return {"value": ub, "time": run_time, "to_draw": self.init_operations_UB_to_draw(op_end_times, solution_data)}


    def __find_UB_greedy_operations(self, less_modes=False):
        """
        find UB using greedy function.
        less_modes: boolean, if true, we will sort by operation modes number
        return dictionary, found UB , how much time its took and draw data
        """
        start = time.time()
        op_end_times = {}
        resorces_time = {}
        for resorce in self.resources.keys():
            resorces_time[resorce] = [{"start": float("inf"), "end": float("inf")}]

        ub = 0
        operations = self.next_operations([])
        # try all avialable operation according to the preferences
        while operations:
            operations = {op: self.operations[op] for op in operations}
            if less_modes:
                operations = min(operations.values(), key=lambda operation: len(operation.modes))
                operations = {operations.number: operations}
            resorces_time, min_time_mode, choisen_operation, best_mode = self.calc_adding_operations(operations, op_end_times, resorces_time.copy())
            ub = max(ub, min_time_mode)
            op_end_times[choisen_operation] = {"mode": best_mode, "end_time": min_time_mode}
            operations = self.next_operations(op_end_times.keys())

        run_time = time.time() - start
        solution_data = "solution in {:.10f} sec\ncreated nodes = 0, max queue size = 0".format(run_time)
        return {"value": ub, "time": run_time, "to_draw": self.init_operations_UB_to_draw(op_end_times, solution_data)}

    def find_UB_ga(self, operations_order, selected_modes):
        """
        find UB using ga algorithm
        operations_order: list of strings, the operations order
        selected_modes: list of strings, the selected mode for each operation
        return dictionary, found UB , how much time its took and draw data
        """
        start = time.time()
        op_end_times = {}
        resorces_time = {}
        for resorce in self.resources.keys():
            resorces_time[resorce] = [{"start": float("inf"), "end": float("inf")}]

        ub = 0
        for op_name in operations_order:
            operation = self.operations[op_name]
            resorces_time, min_time_mode, choisen_operation, best_mode = self.calc_adding_operations({op_name: operation}, op_end_times, resorces_time.copy(), str(selected_modes[int(op_name) - 1]))
            ub = max(ub, min_time_mode)
            op_end_times[choisen_operation] = {"mode": best_mode, "end_time": min_time_mode}

        run_time = time.time() - start
        return {"value": ub, "time": run_time, "to_draw": self.init_operations_UB_to_draw(op_end_times, solution_data="")}


    def create_bellman_ford_graph(self):
        """
        init bellman ford graph with all operations times
        return: Bellman_Ford object
        """
        graph = Bellman_Ford(len(self.operations) + 2)
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
