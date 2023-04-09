from sqlite3 import connect
from sqlite3 import OperationalError
from cplex import infinity
import time
import copy
from random import random
import constraint_equations
from job_operation import Operation
from job_resource import Resource
from bellman_ford import Bellman_Ford
from genetic_algo import GA
from genetic_algo_GA1 import GA_1
from statistics import stdev, mean, median


class Job:
    """
    this class read problems from the database, calculate the UB and LB and create equations.
    """

    def __init__(self, problem_id, cplex_solution=None, ub=None, sort_x=None, reverse=False, repeat=1,
                 create_csv=False, timeout=None, mutation_chance=0.04, multi_times=False, changed_mutation=False,
                 ageing=False, complex_ageing=False):
        self.N = 1e4
        self.problem_id = problem_id
        self.resources = {}
        self.operations = {}
        self.preferences = {}
        self.cplex = {'obj': [], 'ub': [], 'lb': [], 'ctype': "", 'colnames': [], 'rhs': [],
                      'rownames': [], 'sense': "", 'rows': [], 'cols': [], 'vals': []}
        self.x_names = []
        while True:
            try:
                self.sql_problem(problem_id, repeat)
                break
            except OperationalError as e:
                print(e)

        self.count_pref = 0
        for pref in self.preferences.values():
            self.count_pref += len(pref)

        self.count_pref /= len(self.operations)
        if create_csv:
            self.create_csv_file(problem_id)

        self.prec_list = self.remove_duplications_precedence()

        # for each operation save the preferences len to start, used in recursive functions
        self.operations_preferences_position = [-1] * len(self.operations)
        self.__find_rtag_and_tim()
        cross_operations = self.calc_cross_operations()
        self.cross_resources = self.calc_cross_resources(cross_operations)
        self.operations_preferences_len = [-1] * len(self.operations)
        operations_preferences_len = self.calc_longest_path(self.__sort_operations_by_pref_len)
        self.longest_preferences_path = max(operations_preferences_len)
        self.mean_preferences_path = mean(operations_preferences_len)
        for op in self.operations.keys():
            self.__sort_operations_by_pref_len(op, self.operations_preferences_len)

        bf_graph = self.create_bellman_ford_graph([])
        shared_ops = self.get_shared_resources()
        self.LB = bf_graph.bellman_ford_LB(0, len(self.operations) + 1)
        bf_resources_graph = self.create_bellman_ford_graph_with_resources(bf_graph, shared_ops)
        self.LB_res = bf_resources_graph.bellman_ford_LB(0, len(self.operations) + 1)
        self.greedy_all = None
        self.UB = float("inf")
        self.UBs = {}
        for_gas = []
        if ub is "none":
            return

        if ub and "greedy" in ub:
            self.get_all_orders()
            self.greedy_methods(for_gas)

        if ub and "ga" in ub:
            self.ga_methods(ub, timeout, mutation_chance, multi_times, changed_mutation, ageing, complex_ageing,
                            for_gas)

        self.draw_UB = None
        for solution in self.UBs.values():
            if solution["value"] < self.UB:
                self.UB = solution["value"]
                self.draw_UB = solution["to_draw"]

        # if the LB = UB, equations are unnecessary
        if self.UB != self.LB_res and cplex_solution != 'None':
            if sort_x == "pre":
                self.operations = self.__sort_operations_by_preferences(self.__sort_operations_by_pref, reverse)
                self.create_x_i_m_r_l()
            elif sort_x == "res":
                self.__sort_x_by_resources(reverse)
            else:
                self.create_x_i_m_r_l()

            self.__init_cplex_variable_parameters(cplex_solution == "cplex")
            self.__create_equations()

    def ga_methods(self, ub, timeout, mutation_chance, multi_times, changed_mutation, ageing, complex_ageing, for_gas):
        if ub.startswith("ga1"):
            if ub == "ga1_op":
                fitness_function = self.add_resources_to_bellman_ford_graph
                lines = len(self.resources)
                improved_method = "ga1_op"
            else:  # ub == "ga1_res"
                fitness_function = self.add_resources_to_bellman_ford_graph
                lines = len(self.resources)
                improved_method = "ga1_res"

            ga = GA_1(mode_mutation=mutation_chance, data_mutation=mutation_chance, timeout=timeout)
            self.UBs.update(
                {"ga_{}".format(i): ga.solve(self, i, fitness_function, lines, improved_method) for i in range(10)})

        else:
            if ub == "ga2m":
                fitness_function = self.add_resources_to_bellman_ford_graph
                lines = len(self.resources)
                to_draw = True  # False
                solve_using_cross_solutions = True
                improved_method = ""
            elif ub == "ga2s":
                fitness_function = self.find_ub_ga
                lines = 1
                to_draw = True  # False
                solve_using_cross_solutions = False
                improved_method = ""
            elif ub == "ga2s_final":
                fitness_function = self.find_ub_ga
                lines = 1
                to_draw = True  # False
                solve_using_cross_solutions = False
                improved_method = "ga2s_final"
            elif ub == 'ga2s_select_1':
                fitness_function = self.find_ub_ga
                lines = 1
                to_draw = True  # False
                solve_using_cross_solutions = False
                improved_method = "ga2s_select_1"
            elif ub == "ga2s_select_quarter":
                fitness_function = self.find_ub_ga
                lines = 1
                to_draw = True  # False
                solve_using_cross_solutions = False
                improved_method = "ga2s_select_quarter"
            elif ub == 'ga2s_ga2s_all':
                fitness_function = self.find_ub_ga
                lines = 1
                to_draw = False
                solve_using_cross_solutions = False
                improved_method = "one"
                for_gas = []
            elif ub == "greedy_ga2s_ga2s_all":
                fitness_function = self.find_ub_ga
                lines = 1
                to_draw = False
                solve_using_cross_solutions = False
                improved_method = "one"
            elif ub == "ga2s_select_all":
                fitness_function = self.find_ub_ga
                lines = 1
                to_draw = True
                solve_using_cross_solutions = True
                improved_method = "ga2s_select_all"
            elif ub == "ga2s_all" or ub == "greedy_ga2s_all":
                fitness_function = self.find_ub_ga
                lines = 1
                to_draw = True
                solve_using_cross_solutions = True
                improved_method = ""
            else:
                raise (IndexError("invalid option"))

            ga = GA(mode_mutation=mutation_chance, data_mutation=mutation_chance, timeout=timeout,
                    multi_times=multi_times, changed_mutation=changed_mutation, ageing=ageing,
                    complex_ageing=complex_ageing)
            self.UBs.update({"ga_{}".format(i): ga.solve(self, i, fitness_function, solve_using_cross_solutions, lines,
                                                         to_draw, for_gas, improved_method) for i in range(10)})

    def greedy_methods(self, for_gas):
        runs = 1
        loaded_operations = self.get_loaded_resource()
        self.UBs["operations"], for_ga = self.__find_UB_greedy_operations(fixed_operations={})
        for_gas.append(for_ga)
        self.UBs["loaded_shortest_modes"], for_ga = self.__find_UB_greedy_operations(fixed_operations=loaded_operations)
        for_gas.append(for_ga)
        g = [self.__find_ub_greedy(self.__sort_operations_by_pref) for _ in range(runs)]
        self.UBs["mode"], for_ga = min(g, key=lambda s: s[0]["value"])
        self.UBs["mode"]["time"] = calc_random_greedy_time(g)
        for_gas.append(for_ga)
        g = [self.__find_ub_greedy(self.__sort_operations_by_pref_len, reverse=True) for _ in range(runs)]
        self.UBs["greedy_precedence_len_forward"], for_ga = min(g, key=lambda s: s[0]["value"])
        self.UBs["greedy_precedence_len_forward"]["time"] = calc_random_greedy_time(g)
        for_gas.append(for_ga)
        g = [self.__find_UB_greedy_operations(fixed_operations={}, less_modes=True) for _ in range(runs)]
        self.UBs["greedy_precedence_len_backwards"], for_ga = min(g, key=lambda s: s[0]["value"])
        self.UBs["greedy_precedence_len_backwards"]["time"] = calc_random_greedy_time(g)
        for_gas.append(for_ga)
        g = [self.__find_ub_greedy(self.__sort_operations_by_pref_direct, reverse=True) for _ in range(runs)]
        self.UBs["greedy_precedence_sons"], for_ga = min(g, key=lambda s: s[0]["value"])
        self.UBs["greedy_precedence_sons"]["time"] = calc_random_greedy_time(g)
        for_gas.append(for_ga)
        g = [self.__find_ub_greedy(self.__sort_operations_by_pref_all, reverse=True) for _ in range(runs)]
        self.UBs["precedences_all"], for_ga = min(g, key=lambda s: s[0]["value"])
        self.UBs["precedences_all"]["time"] = calc_random_greedy_time(g)
        for_gas.append(for_ga)
        g = [self.__find_ub_greedy(self.__sort_operations_by_pref_time_len, reverse=True) for _ in range(runs)]
        self.UBs["precedences_time"], for_ga = min(g, key=lambda s: s[0]["value"])
        self.UBs["precedences_time"]["time"] = calc_random_greedy_time(g)
        for_gas.append(for_ga)
        g1 = []
        g2 = []
        for _ in range(runs):
            g1.append(self.__find_ub_greedy(self.__get_op_sum_order, reverse=False))
            g2.append(self.__find_ub_greedy(self.__get_op_by_set_order, reverse=False))
        self.UBs["greedy_sum_precedences"], for_ga = min(g1, key=lambda s: s[0]["value"])
        self.UBs["greedy_sum_precedences"]["time"] = calc_random_greedy_time(g1)
        self.UBs["greedy_by_best_precedences"], for_ga = min(g2, key=lambda s: s[0]["value"])
        self.UBs["greedy_by_best_precedences"]["time"] = calc_random_greedy_time(g2)
        for_gas.append(for_ga)
        self.greedy_all = self.UBs[min(self.UBs, key=lambda s: self.UBs[s]["value"])]["value"]

    def remove_duplications_precedence(self):
        # prec_list = {}
        # for name, prec in self.preferences.items():
        #     op_pre = []
        #     for p in prec:
        #         op_pre.append(p.number)
        #         for suc in prec_list[p.number]["pre"]:
        #             if name in prec_list[suc]:
        #                 break
        #         else:
        #             prec_list[p.number]["suc"].append(name)
        #
        #     prec_list[name] = {"pre": op_pre, "suc": []}
        #
        # print("done")
        prec_list = {name: [p.number for p in prec] for name, prec in self.preferences.items()}
        suc_list = {op: [] for op in self.operations}
        suc_list_org = {op: [] for op in self.operations}
        for name, prec in self.preferences.items():
            for p in prec:
                suc_list[p.number].append(name)
                suc_list_org[p.number].append(name)

        can_get_ops = {op: [] for op in self.operations}
        for name, suc in suc_list.items():
            for op, op_suc in suc_list.items():
                if name in op_suc:
                    can_get_ops[op].extend(suc)
                    can_get_ops[op] = list(set(can_get_ops[op]))
                    suc_list[op].extend(suc)
                    suc_list[op] = list(set(suc_list[op]))

        self.suc_list_after_remove = {op: list(set(suc_list[op]) - set(can_get_ops[op])) for op in self.operations}
        # for op, suc in self.suc_list_after_remove.items():
        #     print(f"{op}, {suc}")

    def get_Trs_and_Trf(self, op, mode, Ti):
        op_mode = self.operations[op].get_mode_by_name(mode)
        Trs_and_Trf = []
        for resource in op_mode.resources:
            Ts = resource.get_usage_start_time(op, mode)
            Tf = resource.get_usage_finish_time(op, mode)
            Trs_and_Trf.append({"Resource_ID": resource.number, "Operation_ID": op, "Start_time": Ti+Ts, "Finish_time": Ti+Tf})

        return Trs_and_Trf

    def calc_longest_path(self, sort_function):
        operations_preferences_len = [-1] * len(self.operations)
        sorted(self.operations, key=lambda op: sort_function(op, operations_preferences_len))
        return operations_preferences_len

    def calc_cross_resources(self, cross_operations):
        cross_counter = 0
        for op_1, op_2 in cross_operations:
            operation_1 = self.operations[op_1]
            operation_2 = self.operations[op_2]
            for op_1_mode in operation_1.modes:
                if len(op_1_mode.resources) < 2:
                    continue

                for op_2_mode in operation_2.modes:
                    if len(op_2_mode.resources) < 2:
                        continue

                    op_1_mode_resources = op_1_mode.resources
                    op_2_mode_resources = op_2_mode.resources
                    for res_1 in op_1_mode_resources:
                        for res_2 in op_2_mode_resources:
                            if res_1 != res_2 and res_1 in op_2_mode_resources and res_2 in op_1_mode_resources:
                                op_1_mode_resource_1_start = res_1.get_usage_start_time(op_1, op_1_mode.mode_number)
                                op_1_mode_resource_2_start = res_2.get_usage_start_time(op_1, op_1_mode.mode_number)
                                op_2_mode_resource_1_start = res_1.get_usage_start_time(op_2, op_2_mode.mode_number)
                                op_2_mode_resource_2_start = res_2.get_usage_start_time(op_2, op_2_mode.mode_number)
                                if op_1_mode_resource_1_start <= op_2_mode_resource_1_start and op_1_mode_resource_2_start >= op_2_mode_resource_2_start \
                                        or op_1_mode_resource_1_start >= op_2_mode_resource_1_start and op_1_mode_resource_2_start <= op_2_mode_resource_2_start:
                                    cross_counter += 1
        return cross_counter

    def calc_cross_operations(self):
        operations = {op: set((op)) for op in self.operations.keys()}
        for _ in range(len(self.operations)):
            for op, preferences in self.preferences.items():
                for pref in preferences:
                    operations[op].update(operations[pref.number])

        preferences = []
        for op_1, op_set_1 in operations.items():
            for op_2, op_set_2 in operations.items():
                if op_1 != op_2 and op_1 not in op_set_2 and op_2 not in op_set_1:
                    op_min = min(op_1, op_2)
                    op_max = max(op_1, op_2)
                    preferences.append((op_min, op_max))

        return list(set(preferences))

    def get_mean_r_im(self):
        mean_r_im = 0
        modes = 0
        for operation in self.operations.values():
            for mode in operation.modes:
                mean_r_im += len(mode.resources)
                modes += 1

        return mean_r_im / modes

    def avg_t_im(self):
        pim = []
        for operation in self.operations.values():
            for mode in operation.modes:
                pim.append(mode.tim)

        return mean(pim)

    def avg_h_im(self, pim=None):
        if not pim:
            pim = self.avg_t_im()

        him = []
        for operation in self.operations.values():
            for mode in operation.modes:
                him.append(mode.sim / pim)

        return mean(him)

    def avg_d_im(self):
        duration = []
        for operation in self.operations.values():
            for mode in operation.modes:
                for resource in mode.resources:
                    duration.append(resource.get_usage_duration(mode.op_number, mode.mode_number))

        return mean(duration)

    def get_r_im_range(self, range_mean=False, range_stdev=False, range_median=False, range_range=False,
                       range_cv=False):
        modes_range = []
        modes_median = []
        for operation in self.operations.values():
            mode_min_len = float('inf')
            mode_max_len = 1
            for mode in operation.modes:
                mode_len = len(mode.resources)
                mode_min_len = min(mode_min_len, mode_len)
                mode_max_len = max(mode_max_len, mode_len)
                modes_median.append(mode_len)

            modes_range.append(mode_max_len - mode_min_len)

        try:
            if range_mean:
                return mean(modes_range)

            if range_stdev:
                return stdev(modes_range)

            if range_median:
                return median(modes_median)

            if range_range:
                return max(modes_range) - min(modes_range)

            if range_cv:
                return stdev(modes_range) / mean(modes_range)

        except ZeroDivisionError:
            return 0

    def get_mean_modes(self):
        mean_modes = 0
        for operation in self.operations.values():
            mean_modes += len(operation.modes)

        return mean_modes / len(self.operations)

    def create_csv_file(self, problem_id):
        file = open("problem_{}.csv".format(problem_id), "w")
        file.write("Problem_ID,Oper_ID,Mode_ID,Res_ID,Ts,Tf,Pre_Oper_ID\n")
        for op_name, op in self.operations.items():
            pre_ops = self.preferences[op_name]
            pre_ops = ";".join([operation.number for operation in pre_ops])
            for mode in op.modes:
                for resource in mode.resources:
                    start_time = resource.get_usage_start_time(op_name, mode.mode_number)
                    end_time = start_time + resource.get_usage_duration(op_name, mode.mode_number)
                    line = "{},{},{},{},{},{},{}\n".format(problem_id,
                                                           op_name,
                                                           mode.mode_number,
                                                           resource.number,
                                                           start_time,
                                                           end_time,
                                                           pre_ops)
                    file.write(line)

        file.close()

    def next_operations(self, choices):
        """
        according to the given chose operations, collect all available operation by preferences.
        choices: string[], name of operations that already made/selected
        return: string[], all the available operation
        """
        next_ops = []
        for op_name, preferences in self.preferences.items():
            # don't take operations that already be selected
            if op_name not in choices:
                # for each operation check if all its preference operations in choices list, if so, save the operation
                if not [preference.number for preference in preferences if preference.number not in choices]:
                    next_ops.append(op_name)

        return next_ops

    def read_OpMoRe_query(self, query, repeat):
        """
        take data from OpMoRe query and initialize all class parameters.
        query: dictionary, the OpMoRe query
        repeat: number, number of times to duplicate the problem
        return: None
        """
        OPERATION = 0
        MODE = 1
        RESOURCE = 2
        START = 3
        DURATION = 4
        operations_added = 0  # use to save the number of operations that were created in the last repeat
        for _ in range(repeat):
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
                # add mode to operation with all relevant data
                self.operations[operation].add_mode(mode, self.resources[resource], row[START], row[DURATION])
            operations_added = len(self.operations)

    def get_rearguard_operations(self, operations_in_cycle):
        """
        find and return all operations that no one need them as preferences operations
        operations_in_cycle: number of operations in cycle (operation length / repeat)
        return: list, rearguard operations
        """
        rearguard_operations = [0] * operations_in_cycle
        for pre_list in self.preferences.values():
            for pre_op in pre_list:
                rearguard_operations[int(pre_op.number) - 1] += 1
        return [index + 1 for index, op in enumerate(rearguard_operations) if op == 0]

    def read_priority_query(self, query, repeat):
        """
        take data from Priority query and initialize preferences dictionary.
        query: dictionary, the Priority query
        repeat: number, number of times to duplicate the problem
        return: None
        """
        OPERATION = 0
        PRE_OP = 1
        rearguard_operations = None
        operations_in_cycle = int(len(self.operations) / repeat)
        for loop in range(repeat):
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
                # from repeat 2 to n, every operation that hasn't preferences, use last rearguard operations as her
                # preferences operations
                for operation_number in range(loop * operations_in_cycle + 1, (loop + 1) * operations_in_cycle + 1):
                    if not self.preferences[str(operation_number)]:
                        for pre_op in rearguard_operations:
                            op = str(operations_in_cycle * (loop - 1) + pre_op)
                            self.preferences[str(operation_number)].append(self.operations[op])

    def sql_problem(self, problem_id, repeat):
        """
        read problem data from the DB using sql query and initialize all class parameters.
        the DB contains 2 tables with problem data:
            * OpMoRe: the start time and the duration of resource use by operation in some mode.
            * Priority: operations and there preferences operations
        from each table we take the relevant data by using the problem_ID.
        problem_ID: number, the wanted problem number to be solved
        repeat: number, number of times to duplicate the problem
        return: None
        """
        conn = connect('data.db')
        c = conn.cursor()
        c.execute("SELECT Oper_ID, Mode_ID, Res_ID, Ts,(Tf - Ts) AS DUR FROM OpMoRe where Problem_ID = {0} ORDER BY "
                  "Oper_ID, Mode_ID, Res_ID".format(problem_id))
        opmode_query = c.fetchall()
        c.execute(
            "SELECT Suc_Oper_ID, Pre_Oper_ID FROM Priority where Problem_ID = {0} ORDER BY Suc_Oper_ID, Pre_Oper_ID".format(
                problem_id))
        priority_query = c.fetchall()
        conn.close()

        self.read_OpMoRe_query(opmode_query, repeat)
        self.read_priority_query(priority_query, repeat)

    def __find_rtag_and_tim(self):
        """
        set the r and the Tim for all modes
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
        return: dictionary of operations
        """
        # create a list that contains all operations number and sorted by their preferences length
        operations_preferences_len = [-1] * len(self.operations)
        op_order = sorted(self.operations, key=lambda op: (sort_function(op, operations_preferences_len), random()),
                          reverse=reverse)
        operations = {}
        # create dictionary of [operation number: operation object]
        collected_ops = []
        ops = self.next_operations(collected_ops)
        while ops:
            next_op = min(ops, key=lambda op: op_order.index(op))
            operations[next_op] = self.operations[next_op]
            collected_ops.append(next_op)
            ops = self.next_operations(collected_ops)
        return operations

    def __sort_operations_by_pref_len(self, op, operations_preferences_len):
        """
        a recursive function that calculate the max number of operation that came after the given operation
        op: string, operation name
        operations_preferences_len: list, save the len for each operation to save not needed calculations
        return: number, the max len of the operation that need this operation
        """
        if operations_preferences_len[int(op) - 1] == -1:
            preferences_len = [0]
            # check every operation
            for operation, preferences in self.preferences.items():
                # if operation have the given operation in its preferences
                if self.operations[op] in preferences:
                    # check the len of the operation and add 1 to the len
                    preferences_len.append(
                        self.__sort_operations_by_pref_len(operation, operations_preferences_len) + 1)

            operations_preferences_len[int(op) - 1] = max(preferences_len)
        return operations_preferences_len[int(op) - 1]

    def __sort_operations_by_pref_time_len(self, op, operations_preferences_len):
        """
        a recursive function that calculate the max number of operation that came after the given operation
        op: string, operation name
        operations_preferences_len: list, save the len for each operation to save not needed calculations
        return: number, the max len of the operation that need this operation
        """
        if operations_preferences_len[int(op) - 1] == -1:
            preferences_len = [0]
            # check every operation
            for operation, preferences in self.preferences.items():
                # if operation have the given operation in its preferences
                if self.operations[op] in preferences:
                    # check the len of the operation and add 1 to the len
                    preferences_len.append(
                        self.__sort_operations_by_pref_len(operation, operations_preferences_len) + self.operations[
                            op].get_min_tim())

            operations_preferences_len[int(op) - 1] = max(preferences_len)
        return operations_preferences_len[int(op) - 1]

    def __sort_operations_by_pref_direct(self, op, operations_preferences_len):
        """
        a recursive function that calculate the max number of operation that came after the given operation
        op: string, operation name
        operations_preferences_len: list, save the len for each operation to save not needed calculations
        return: number, the max len of the operation that need this operation
        """
        preferences_count = -1
        if operations_preferences_len[int(op) - 1] == -1:
            preferences_count = 0
            # check every operation
            for preferences in self.preferences.values():
                # if operation have the given operation in its preferences
                if self.operations[op] in preferences:
                    # check the len of the operation and add 1 to the len
                    preferences_count += 1

        return preferences_count

    def __sort_operations_by_pref_all(self, op, operations_preferences_len, collected_ops=None):
        """
        a recursive function that calculate the max number of operation that came after the given operation
        op: string, operation name
        operations_preferences_len: list, save the len for each operation to save not needed calculations
        return: number, the max len of the operation that need this operation
        """
        if not collected_ops:
            collected_ops = []
        preferences_all = -1
        if operations_preferences_len[int(op) - 1] == -1:
            preferences_all = 0
            # check every operation
            for operation, preferences in self.preferences.items():
                # if operation have the given operation in its preferences
                if self.operations[op] in preferences:
                    if op not in collected_ops:
                        # check the len of the operation and add 1 to the len
                        collected_ops.append(operation)
                        preferences_all += self.__sort_operations_by_pref_all(operation, operations_preferences_len,
                                                                              collected_ops) + 1

        return preferences_all

    def __sort_operations_by_pref(self, op, _):
        """
        call to __sort_operations_by_pref_recursive with all preferences operations
        op: string, operation name
        return: number
        """
        if self.operations_preferences_position[int(op) - 1] == -1:
            self.operations_preferences_position[int(op) - 1] = self.__sort_operations_by_pref_recursive(
                self.preferences[op])
        return self.operations_preferences_position[int(op) - 1]

    def __sort_operations_by_pref_recursive(self, op_list):
        """
        a recursive function that calculate the max number of operation that need to be pass to arrive
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

    def add_mode_cross_resources(self, start_time, mode_resources_time, mode, op_mode):
        """
        try to add mode with cross resources if neseraly.
        start_time: minimum start time, according to the preferences'
        mode_resources_time: dictionary, the resources usage time
        mode: Mode, mode object
        op_mode: string, "operation_mode" string
        """
        start_indexs = {}
        # skip all not relevant options - by preferences
        for resource in mode.resources:  # O(Rim*Rl)
            start_indexs[resource.number] = 1
            while mode_resources_time[resource.number][start_indexs[resource.number]]["end"] <= start_time:
                start_indexs[resource.number] += 1

        index = copy.deepcopy(start_indexs)

        while True:  # O(Rim*Rl)
            # check all resources
            resource_number = None
            resource_usage = None
            for resource in mode.resources:  # O(Rim)
                if not resource_number or mode_resources_time[resource.number][index[resource.number]]["end"] < \
                        mode_resources_time[resource_number][index[resource_number]]["end"]:
                    resource_number = resource.number
                    resource_usage = resource.usage[op_mode]

            # resource usage data, from the Resource object
            current_usage = mode_resources_time[resource_number][index[resource_number]]
            if current_usage["begin"] != float("inf"):
                next_usage = mode_resources_time[resource_number][index[resource_number] + 1]
                # if the usage starts before the index usage
                if current_usage["end"] + resource_usage["start_time"] + resource_usage["duration"] > next_usage["begin"]:
                    index[resource_number] += 1
                    continue

                min_start_time = max(start_time, current_usage["end"] - resource_usage["start_time"])

            else:
                pre_usage = mode_resources_time[resource_number][index[resource_number] - 1]
                min_start_time = max(start_time, pre_usage["end"] - resource_usage["start_time"])

            for resource in mode.resources:  # O(Rim*Rl)
                resource_usage = resource.usage[op_mode]
                for next_index in range(start_indexs[resource.number], len(mode_resources_time[resource.number])):
                    current_usage = mode_resources_time[resource.number][next_index]
                    if min_start_time + resource_usage["start_time"] < current_usage["end"]:
                        break

                if current_usage["end"] < min_start_time + resource_usage["start_time"] + resource_usage["duration"] or \
                        current_usage["begin"] <= min_start_time + resource_usage["start_time"] or \
                        (current_usage["begin"] > min_start_time + resource_usage["start_time"] and
                         current_usage["begin"] < min_start_time + resource_usage["start_time"] + resource_usage[
                             "duration"]):
                    index[resource_number] = min(index[resource_number] + 1,
                                                 len(mode_resources_time[resource_number]) - 1)
                    break

            else:
                return min_start_time

    def calc_adding_mode(self, pre_dur, mode_resources_time, mode):
        """
        calculate the resources end time according to the selected operations before.
        pre_dur: numbers[], each cell contains preference operations end time.
        mode_resources_time: dictionary, end time of each resource.
        mode: Mode, the mode that want to calculate.
        return: number - the end time of the mode, dictionary - the end time of every resource
        """
        op_mode = "{},{}".format(mode.op_number, mode.mode_number)
        # add the end time of each resource to the list of end time of the preferences
        mode_start_time = self.add_mode_cross_resources(max(pre_dur), mode_resources_time, mode, op_mode)
        # take the biggest end time to start the mode
        # mode_start_time = max(pre_dur)
        # for each resource in mode, add it start time + duration to the mode start time
        for resource in mode.resources:
            usage = resource.usage[op_mode]
            new_usage = {"begin": mode_start_time + usage["start_time"],
                         "end": mode_start_time + usage["duration"] + usage["start_time"], "operation": mode.op_number}
            for index, value in enumerate(mode_resources_time[resource.number][1:], 1):
                # Assuming y is in increasing order.
                if value['begin'] > new_usage['begin']:
                    mode_resources_time[resource.number].insert(index, new_usage)
                    break

        return mode_start_time + mode.tim, mode_resources_time

    def calc_adding_operations(self, operations, op_end_times, resources_time, selected_mode=None):
        """
        add operation with the best mode.
        operations: list of Operation, part of job operations
        op_end_times: dictionary, the end time of each operation
        resources_time: dictionary, resources end time
        selected_mode: dictionary, {op: mode} if we want to select specific mode
        return: dictionary
        """
        min_time_mode = float("inf")
        best_resources_time = None
        chosen_operation = None
        best_mode = None
        for name, operation in operations.items():
            modes = None
            pre_dur = [0]
            # save all preferences operation end time
            for pre in self.preferences[name]:
                pre_dur.append(op_end_times[pre.number]["end_time"])

            if selected_mode and name in selected_mode:
                # modes = [mode for mode in operation.modes if mode.mode_number == selected_mode]
                for mode in operation.modes:
                    if mode.mode_number == selected_mode[name]:
                        modes = [mode]
                        break

            else:
                modes = operation.modes

            # check all modes and take the best
            for mode in modes:
                mode_time, mode_resources_time = self.calc_adding_mode(pre_dur[:], copy.deepcopy(resources_time), mode)
                if min_time_mode > mode_time:
                    best_resources_time = mode_resources_time
                    min_time_mode = mode_time
                    chosen_operation = mode.op_number
                    best_mode = mode

        return best_resources_time, min_time_mode, chosen_operation, best_mode

    def calc_adding_mode_stupid(self, pre_dur, mode_resources_time, mode):
        """
        calculate the resources end time according to the selected operations before.
        pre_dur: numbers[], each cell contains preference operations end time.
        mode_resources_time: dictionary, end time of each resource.
        mode: Mode, the mode that want to calculate.
        return: number - the end time of the mode, dictionary - the end time of every resource
        """
        op_mode = "{},{}".format(mode.op_number, mode.mode_number)
        # add the end time of each resource to the list of end time of the preferences
        for resource in mode.resources:
            usage = resource.usage[op_mode]
            # if resource start time in the mode != 0, it's mean that the resource need only after that time
            pre_dur.append(mode_resources_time[resource.number]["end"] - usage["start_time"])

        # take the biggest end time to start the mode
        mode_start_time = max(pre_dur)
        # for each resource in mode, add it start time + duration to the mode start time
        for resource in mode.resources:
            usage = resource.usage[op_mode]
            mode_resources_time[resource.number] = {"begin": mode_start_time,
                                                    "end": mode_start_time + usage["start_time"] + usage["duration"]}

        return mode_start_time + mode.tim, mode_resources_time

    def calc_adding_operations_stupid(self, operations, op_end_times, resources_time, selected_mode=None):
        best_resources_time = None
        min_time_mode = None
        chosen_operation = None
        best_mode = None
        for name, operation in operations.items():
            modes = None
            pre_dur = []
            for pre in self.preferences[name]:
                pre_dur.append(op_end_times[pre.number]["end_time"])
            min_time_mode = float("inf")
            if selected_mode:
                # modes = [mode for mode in operation.modes if mode.mode_number == selected_mode]
                for mode in operation.modes:
                    if mode.mode_number == selected_mode[name]:
                        modes = [mode]
                        break

            else:
                modes = operation.modes

            for mode in modes:
                mode_time, mode_resources_time = self.calc_adding_mode_stupid(pre_dur[:], copy.deepcopy(resources_time),
                                                                              mode)
                if min_time_mode > mode_time:
                    best_resources_time = mode_resources_time
                    min_time_mode = mode_time
                    chosen_operation = mode.op_number
                    best_mode = mode

        return best_resources_time, min_time_mode, chosen_operation, best_mode

    def init_operations_ub_to_draw(self, op_end_times, solution_data):
        """
        creat dictionary with all data to draw the solution, this dictionary contains: mode: the selected mode number
        for each operation start: operation start time duration: operation duration resources: for each operation we
        save in dictionary {"start" : resource global start time, "duration" : resource duration} with this data we
        can draw the solution if the UB = LB op_end_times: dictionary, for each operation  we save {"mode": Mode
        object, "end_time": operation global end time } solution_data: string with solution data: time,
        number of nodes and queue size return dictionary {"operations": dictionary, "title": string, "choices_modes":
        list of strings}
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
                operations[operation_name]["resources"][resource.number] = {
                    "start": operation_start_time + resource_start_time, "duration": resource_duration}

        return {"operations": operations, "title": solution_data, "choices_modes": choices_modes}

    def get_all_orders(self):
        operations_sum_order = []
        order_pref_len = self.__sort_operations_by_preferences(self.__sort_operations_by_pref_len, reverse=True)
        operations_sum_order.append(order_pref_len)
        order_pref_time = self.__sort_operations_by_preferences(self.__sort_operations_by_pref_time_len, reverse=True)
        operations_sum_order.append(order_pref_time)
        order_pref_direct = self.__sort_operations_by_preferences(self.__sort_operations_by_pref_direct, reverse=True)
        operations_sum_order.append(order_pref_direct)
        order_pref_all = self.__sort_operations_by_preferences(self.__sort_operations_by_pref_all, reverse=True)
        operations_sum_order.append(order_pref_all)
        order_pref = self.__sort_operations_by_preferences(self.__sort_operations_by_pref, reverse=False)
        operations_sum_order.append(order_pref)
        op_sum_value = {}
        op_by_best_value = {}
        for order in operations_sum_order:
            for i, op in enumerate(order):
                if op in op_sum_value:
                    op_sum_value[op] += i
                    op_by_best_value[op] += (i,)
                else:
                    op_sum_value[op] = i
                    op_by_best_value[op] = (i,)

        self.operations_sum_order = op_sum_value
        self.operations_by_best_order = op_by_best_value

    def __get_op_sum_order(self, op, _):
        return self.operations_sum_order[op]

    def __get_op_by_set_order(self, op, _):
        return self.operations_by_best_order[op]

    def __find_ub_greedy(self, sort_function, reverse=False):
        """
        find UB using greedy function.
        sort_function: function, the function that return the operations order
        reverse: boolean, send to the sort_function
        return dictionary, found UB , how much time its took and draw data
        """
        start = time.time()
        for_ga = {"modes": [], "data": [], "makespan": -1}
        op_end_times = {}
        resources_time = {}
        for resource in self.resources.keys():
            resources_time[resource] = [{"begin": float("-inf"), "end": 0, "operation": "-1"},
                                      {"begin": float("inf"), "end": float("inf"), "operation": "-1"}]

        ub = 0
        for name, operation in self.__sort_operations_by_preferences(sort_function, reverse=reverse).items():
            resources_time, min_time_mode, chosen_operation, best_mode = self.calc_adding_operations({name: operation},
                                                                                                     op_end_times,
                                                                                                     resources_time.copy())
            ub = max(ub, min_time_mode)
            op_end_times[chosen_operation] = {"mode": best_mode, "end_time": min_time_mode}
            for_ga["modes"].append(best_mode.mode_number)
            for_ga["data"].append(chosen_operation)

        run_time = time.time() - start
        solution_data = "solution in {:.10f} sec\ncreated nodes = 0, max queue size = 0".format(run_time)
        op = [[i["operation"] for i in d if "-1" != i["operation"]] for r, d in resources_time.items()]
        cross_resources = self.ga_check_cross_solution(op)
        for_ga["modes"] = [m for i, m in sorted(zip(for_ga["data"], for_ga["modes"]), key=lambda pair: int(pair[0]))]
        for_ga["data"] = [for_ga["data"]]
        for_ga["makespan"] = ub
        for_ga["origin"] = {"greedy": 100}
        return {"value": ub, "time": run_time, "to_draw": self.init_operations_ub_to_draw(op_end_times, solution_data),
                "feasibles": 100, "cross_resources": cross_resources, "cross_best_solution": cross_resources > 0,
                "improved_generation": -1, "origin": {"greedy": 100}}, for_ga

    def __find_UB_greedy_operations(self, fixed_operations, less_modes=False):
        """
        find UB using greedy function.
        less_modes: boolean, if true, we will sort by operation modes number
        return dictionary, found UB , how much time its took and draw data
        """
        start = time.time()
        for_ga = {"modes": [], "data": [], "makespan": -1}
        op_end_times = {}
        resources_time = {}
        for resource in self.resources.keys():
            resources_time[resource] = [{"begin": float("-inf"), "end": 0, "operation": "-1"},
                                        {"begin": float("inf"), "end": float("inf"), "operation": "-1"}]

        ub = 0
        operations = self.next_operations([])
        # try all available operation according to the preferences
        while operations:
            operations = {op: self.operations[op] for op in operations}
            if less_modes:
                operations = min(operations.values(), key=lambda operation: (len(operation.modes), random()))
                operations = {operations.number: operations}
            elif fixed_operations:
                fixed_ops = {}
                for op in operations.values():
                    if op.number in fixed_operations.keys():
                        fixed_ops[op.number] = op

                operations = fixed_ops if fixed_ops else operations

            resources_time, min_time_mode, chosen_operation, best_mode = self.calc_adding_operations(operations,
                                                                                                     op_end_times,
                                                                                                     resources_time.copy(),
                                                                                                     selected_mode=fixed_operations)
            ub = max(ub, min_time_mode)
            op_end_times[chosen_operation] = {"mode": best_mode, "end_time": min_time_mode}
            for_ga["modes"].append(best_mode.mode_number)
            for_ga["data"].append(chosen_operation)
            operations = self.next_operations(op_end_times.keys())

        run_time = time.time() - start
        solution_data = "solution in {:.10f} sec\ncreated nodes = 0, max queue size = 0".format(run_time)
        op = [[i["operation"] for i in d if "-1" != i["operation"]] for r, d in resources_time.items()]
        cross_resources = self.ga_check_cross_solution(op)
        for_ga["modes"] = [m for i, m in sorted(zip(for_ga["data"], for_ga["modes"]), key=lambda pair: int(pair[0]))]
        for_ga["data"] = [for_ga["data"]]
        for_ga["makespan"] = ub
        for_ga["origin"] = {"greedy": 100}
        return {"value": ub, "time": run_time, "to_draw": self.init_operations_ub_to_draw(op_end_times, solution_data),
                "feasibles": 100, "cross_resources": cross_resources, "cross_best_solution": cross_resources > 0,
                "improved_generation": -1, "origin": {"greedy": 100}}, for_ga

    def find_ub_ga(self, operations_order, selected_modes, solve_using_cross_solutions=True):
        """
        find UB using ga algorithm
        operations_order: list of strings, the operations order
        selected_modes: list of strings, the selected mode for each operation
        return dictionary, found UB , how much time its took and draw data
        """
        start = time.time()
        op_end_times = {}
        resources_time = {}
        for resource in self.resources.keys():
            if solve_using_cross_solutions:
                resources_time[resource] = [{"begin": float("-inf"), "end": 0, "operation": "-1"},
                                            {"begin": float("inf"), "end": float("inf"), "operation": "-1"}]
            else:
                resources_time[resource] = {"begin": 0, "end": 0}

        ub = 0
        for operations in operations_order:
            for op_name in operations:
                operation = self.operations[op_name]
                if solve_using_cross_solutions:
                    resources_time, min_time_mode, chosen_operation, best_mode = self.calc_adding_operations(
                        {op_name: operation}, op_end_times, resources_time.copy(),
                        {op_name: str(selected_modes[int(op_name) - 1])})
                    ub = max(ub, min_time_mode)
                    op_end_times[chosen_operation] = {"mode": best_mode, "end_time": min_time_mode}

                else:
                    resources_time, min_time_mode, chosen_operation, best_mode = self.calc_adding_operations_stupid(
                        {op_name: operation}, op_end_times, resources_time.copy(),
                        {op_name: str(selected_modes[int(op_name) - 1])})
                    ub = max(ub, min_time_mode)
                    op_end_times[chosen_operation] = {"mode": best_mode, "end_time": min_time_mode}

        run_time = time.time() - start
        solution_data = "solution in {:.10f} sec\ncreated nodes = 0, max queue size = 0".format(run_time)
        if solve_using_cross_solutions:
            op = [[i["operation"] for i in d if "-1" != i["operation"]] for r, d in resources_time.items()]
            cross_resources = self.ga_check_cross_solution(op)
            return {"value": ub, "time": run_time,
                    "to_draw": self.init_operations_ub_to_draw(op_end_times, solution_data=""),
                    "cross_resources": cross_resources}
        else:
            return {"value": ub, "time": run_time, "to_draw": self.init_operations_ub_to_draw(op_end_times, solution_data), "cross_resources": 0}

    def ga_check_cross_solution(self, operations_list):
        resources_order = {}
        for resource in operations_list:
            for index, operation in enumerate(resource):
                if operation not in resources_order:
                    resources_order[operation] = set()
                resources_order[operation].update(resource[index:])

        count = 0
        for operation, resource_list in resources_order.items():
            for operation_2 in resource_list:
                if operation != operation_2 and operation in resources_order[operation_2]:
                    count += 1

        return count / 2

    def check_cross_solution(self, data_list, modes_list, foo):
        operations_coef = {str(pos): set() for pos in range(1, len(modes_list) + 1)}
        copy_data_list = [resources[:] for resources in data_list]
        for res_number, operations in enumerate(copy_data_list, start=1):
            index = 0
            # remove all not needed resource from the resources list
            while index < len(operations):
                mode_resources = self.operations[operations[index]].get_mode_by_name(
                    str(modes_list[int(operations[index]) - 1])).resources
                needed_resource = any(str(res_number) == resource.number for resource in mode_resources)
                if not needed_resource:
                    operations.remove(operations[index])
                # if the resource is used, check next resource and add 1 to the number of used resources
                else:
                    index += 1

        count = 0
        for operations in copy_data_list:
            for pos, op in enumerate(operations[:-1], start=1):
                follow_operations = set(operations[pos:])
                for follow_op in follow_operations:
                    if op in operations_coef[follow_op]:
                        count += 1
                else:
                    operations_coef[str(op)].update(follow_operations)

        return count

    def add_resources_to_bellman_ford_graph(self, resources_list, modes_list, solve_using_cross_solutions=True):
        start = time.time()
        ga_bf_graph = self.create_bellman_ford_graph(modes_list)
        copy_resources_list = [resources[:] for resources in resources_list]
        for res_number, operations in enumerate(copy_resources_list, start=1):
            index = 0
            # remove all not needed resource from the resources list
            while index < len(operations):
                mode_resources = self.operations[operations[index]].get_mode_by_name(
                    str(modes_list[int(operations[index]) - 1])).resources
                needed_resource = any(str(res_number) == resource.number for resource in mode_resources)
                if not needed_resource:
                    operations.remove(operations[index])
                # if the resource is used, check next resource and add 1 to the number of used resources
                else:
                    index += 1

        preference = {}
        for res_number, operations in enumerate(copy_resources_list, start=1):
            if len(operations) > 1:
                resource = self.resources[str(res_number)]
                for op, next_op in zip(operations, operations[1:]):
                    mode = str(modes_list[int(op) - 1])
                    next_mode = str(modes_list[int(next_op) - 1])
                    i1tf_minus_i2fs = resource.get_usage_start_time(op, mode) + resource.get_usage_duration(op,
                                                                                                            mode) - resource.get_usage_start_time(
                        next_op, next_mode)
                    op_next_op = "{}_{}".format(op, next_op)
                    if op_next_op in preference:
                        preference[op_next_op] = max(preference[op_next_op], i1tf_minus_i2fs)
                    else:
                        preference[op_next_op] = i1tf_minus_i2fs

        for op_next_op, max_delay in preference.items():
            op, next_op = op_next_op.split("_")
            ga_bf_graph.addEdge(int(op), int(next_op), max_delay)

        # return ga_bf_graph
        run_time = time.time() - start
        dummy = 1
        cross_resources = 0
        value = ga_bf_graph.bellman_ford_LB(0, len(self.operations) + 1)
        if value:
            cross_resources = self.check_cross_solution(resources_list, modes_list, dummy)

        return {"value": value, "time": run_time, "to_draw": None, "cross_resources": cross_resources}

    def create_bellman_ford_graph_with_resources(self, bf_graph, shared_ops):
        for op, preferences in self.preferences.items():
            min_start = float("inf") if preferences else 0
            resources = {"0": 0}
            for preference in preferences:
                for pre in preferences:
                    if preference in self.preferences[pre.number]:
                        continue

                min_start = min(min_start, bf_graph.dist[int(preference.number)])
                for name, dur in shared_ops[preference.number].items():
                    if name in resources:
                        resources[name] += dur
                    else:
                        resources[name] = dur

            res = max(resources, key=lambda r: resources[r])
            bf_graph.addEdge(0, int(op), min_start + resources[res])

        return bf_graph

    def create_bellman_ford_graph(self, modes):
        """
        init bellman ford graph with all operations times
        return: Bellman_Ford object
        """
        bf_graph = Bellman_Ford(len(self.operations) + 2)
        for op in self.__sort_operations_by_preferences(self.__sort_operations_by_pref).keys():
            for pre_op in self.preferences[op]:
                if modes:
                    mode_number = modes[int(pre_op.number) - 1]
                    bf_graph.addEdge(int(pre_op.number), int(op), pre_op.get_mode_by_name(str(mode_number)).tim)
                else:
                    bf_graph.addEdge(int(pre_op.number), int(op), pre_op.get_min_tim())

            bf_graph.addEdge(0, int(op), 0)
            if modes:
                mode_number = modes[int(op) - 1]
                bf_graph.addEdge(int(op), len(self.operations) + 1,
                                 self.operations[op].get_mode_by_name(str(mode_number)).tim)
            else:
                bf_graph.addEdge(int(op), len(self.operations) + 1, self.operations[op].get_min_tim())

        return bf_graph

    def get_loaded_resource(self):
        resources = {}
        for op_name, op in self.operations.items():
            mode = op.get_shortest_mode()
            op_mode = f"{op_name},{mode.mode_number}"
            for resource in mode.resources:
                if resource.number in resources:
                    resources[resource.number]["duration"] += resource.usage[op_mode]["duration"]
                    resources[resource.number]["operations"][op_name] = mode.mode_number
                else:
                    resources[resource.number] = {}
                    resources[resource.number]["duration"] = resource.usage[op_mode]["duration"]
                    resources[resource.number]["operations"] = {op_name: mode.mode_number}

        res = max(resources, key=lambda res: resources[res]["duration"])
        return resources[res]["operations"]

    def get_shared_resources(self):
        shared_ops = {}
        for op_name, op in self.operations.items():
            shared_resources = {}
            for mode in op.modes:
                for resource in self.resources.values():
                    op_mode = f"{op_name},{mode.mode_number}"
                    if op_mode not in resource.usage:
                        duration = 0
                    else:
                        usage = resource.usage[op_mode]
                        if resource.number in shared_resources:
                            duration = min(usage["duration"], shared_resources[resource.number])
                        else:
                            duration = usage["duration"]

                    shared_resources[resource.number] = duration

            shared_ops[op_name] = shared_resources

        # remove 0 value resources
        small_shared_ops = {}
        for op, resources in shared_ops.items():
            shared_resources = {}
            for r, d in resources.items():
                if d != 0:
                    shared_resources[r] = d

            small_shared_ops[op] = shared_resources

        return small_shared_ops

    def __sort_x_by_resources(self, reverse=False):
        """
        create and sort the Xi,m,r,l according to the usage resources for the cplex equations.
        reverse: boolean, True - sort from the most usage resources,
            False - sort from the lass usage resources
        return None
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


def calc_random_greedy_time(runs):
    s = 0
    for d in runs:
        s += d[0]["time"]

    return s
