import random
import time
import csv
from threading import Timer
from datetime import datetime


class InfeasibleException(Exception):
    def __init__(self, infeasibles_counter, feasibles_counter, run_time, best_solution):
        self.feasibles = feasibles_counter
        self.infeasibles = infeasibles_counter
        self.run_time = run_time
        self.best_solution = best_solution

    def __str__(self):
        return str("InfeasibleException:\nafter = {}s, infeasibles_counter = {}, feasibles_counter = {}, best_solution = {}").format(self.run_time, self.infeasibles, self.feasibles, self.best_solution)

class GA:

    """
    this class present a genetic algorithm.
    this class resive fitness function and data about the genetic options:
        population_size, mutation and number of generations
    by the given data, the algorithm try to solve the problem
    """

    def __init__(self, generations=50, population_size=16, mode_mutation=0.04, data_mutation=0.04, timeout=None, multi_times=False, changed_mutation=False, ageing=False, complex_ageing=False):
        self.generations = generations
        self.current_generation = 0
        self.population_size = population_size
        self.mode_mutation = self.base_mode_mutation = mode_mutation
        self.data_mutation = self.base_data_mutation = data_mutation
        self.timeout = timeout
        self.multi_times = multi_times
        self.changed_mutation = changed_mutation
        self.ageing = ageing
        self.infeasibles_counter = 0
        self.feasibles_counter = 0
        self.exit = False
        if ageing:
            self.next_generation = self.next_generation_ageing_func
            if complex_ageing:
                self.calc_ageing = self.complex_ageing_function
            else:
                self.calc_ageing = self.ageing_function
        else:
            self.next_generation = self.next_generation_func
        self.min_solutions_to_calculate = (generations + 1) * population_size


    def reset_ga_params(self):
        self.mode_mutation = self.base_mode_mutation
        self.data_mutation = self.base_data_mutation


    def raiseTimeout(self):
        self.exit = True


    def first_population(self, operations, preferences_function, fitness_function, solve_using_cross_solutions, improved_method, resources_number=1):
        """
        create the first population with the operation and preferences data
        operations: list of Operation, all operation data
        preferences_function: function, according to this function the gen created
        return: list of dictionary, [{"modes": number, "operations": number}]
        """
        self.infeasibles_counter = 0
        self.feasibles_counter = 0
        self.current_generation = 0
        self.population = []
        self.solution_collected_data = []
        for _ in range(self.population_size):
            gen, solution_data = self.__create_feasible_gen(operations, preferences_function, fitness_function, resources_number, solve_using_cross_solutions, improved_method)
            self.population.append(gen)
            self.solution_collected_data.append(solution_data)

        return self.population, self.solution_collected_data


    def __create_feasible_gen(self, operations, preferences_function, fitness_function, resources_number, solve_using_cross_solutions, improved_method=""):
        while not self.exit:
            modes = []
            data = [[] for i in range(resources_number)]
            # for each operation randomly select mode
            for op in operations.values():
                modes.append(random.randint(1, len(op.modes)))

            # the preferences_function return all operation that can be start after all already done operations
            # according to the preferences limits
            for resource in range(resources_number):
                possible_resources = preferences_function(data[resource])
                while possible_resources:
                    # randomly choise the next operation from all available operations
                    data[resource].append(random.choice(possible_resources))
                    possible_resources = preferences_function(data[resource])

            if improved_method == "ga2s_select_all":
                solution = fitness_function(data, modes, True)
                solution_2 = fitness_function(data, modes, False)
                solution = solution if solution["value"] < solution_2["value"] else solution
            else:
                solution = fitness_function(data, modes, solve_using_cross_solutions)

            if solution["value"]:
                # for each gen, save the choisen modes and the operations order
                self.feasibles_counter += 1
                return {"modes": modes, "data": data, "makespan": solution["value"], "origin": {"ga": 100}}, solution

            else:
                self.infeasibles_counter += 1
                if self.infeasibles_counter > 10000 and self.feasibles_counter / self.infeasibles_counter < 0.001:
                    self.solution_collected_data.append({"value": float('inf'), "cross_resources": -1})
                    raise InfeasibleException(self.infeasibles_counter, self.feasibles_counter, time.time() - self.start, self.solution_collected_data[0]["value"])

        self.solution_collected_data.append({"value": float('inf'), "cross_resources": -1})
        raise InfeasibleException(self.infeasibles_counter, self.feasibles_counter, time.time() - self.start, self.solution_collected_data[0]["value"])


    def __calc_origin(self, parent_1, parent_2):
        side = [parent_1["origin"], parent_2["origin"]]
        sides = {}
        for s in side:
            for k,v in s.items():
                if k in sides:
                    sides[k] += v/2
                else:
                    sides[k] = v/2
        
        return sides


    def __crossover(self, parent_1, parent_2, mode_index, res_index):
        """
        crossover between two parents to create 2 new sons.
        parent_1: dictionary, gen data
        parent_2: dictionary, gen data
        mode_index: number, index for the modes crossover
        op_index: number, index for the operations crossover
        return: dictionary, new son
        """
        # mode crossover
        # take from 0 to index-1 from the first parent and from index to the end from the second parent
        modes = parent_1["modes"][0:mode_index] + parent_2["modes"][mode_index:]
        # operation crossover
        # take from 0 to index-1 from the first parent all not selected operations from the second parent
        data = [[] for i in range(len(parent_1["data"]))]
        for res_number, res in enumerate(parent_2["data"]):
            data[res_number] = parent_1["data"][res_number][0:res_index]
            for p2_res in res:
                if p2_res not in data[res_number]:
                    data[res_number].append(p2_res)

        self.__calc_origin(parent_1, parent_2)
        # return the new son
        return {"modes": modes, "data": data, "origin": self.__calc_origin(parent_1, parent_2)}


    def crossover(self, parent_1, parent_2):
        """
        crossover between two parents to create 2 new sons.
        parent_1: dictionary, gen data
        parent_2: dictionary, gen data
        return: 2 dictionary, 2 new sons
        """
        # lattery the cross index, one for the modes and another for the operations
        max_index = len(parent_1["modes"]) - 1
        mode_index = random.randint(1, max_index)
        res_index = random.randint(1, max_index)
        # create 2 new sons
        son_1 = self.__crossover(parent_1, parent_2, mode_index, res_index)
        son_2 = self.__crossover(parent_2, parent_1, mode_index, res_index)
        return son_1, son_2


    def mutation_process(self, son, operations, preferences_function):
        if self.multi_times:
            mode_mutation = self.mode_mutation
            data_mutation = self.data_mutation
            while random.random() <= mode_mutation:
                son = self.mode_mutation_process(son, operations)
                mode_mutation /= 2

            while random.random() <= data_mutation:
                son = self.data_mutation_process(son, preferences_function)
                data_mutation /= 2

        else:
            # if the lottery number less then the motation chance, do the modes motation
            if random.random() <= self.mode_mutation:
                son = self.mode_mutation_process(son, operations)

            # if the lottery number less then the motation chance, do the operations motation
            if random.random() <= self.data_mutation:
                son = self.data_mutation_process(son, preferences_function)

        return son


    def mode_mutation_process(self, son, operations):
        """
        do motation on the new son.
        son: dictionary, son's data
        operations: list of Operation, all operation data
        return: dictionary, the son after the motation, if was
        """
        # lottery an operation on which we will do the motation
        op = random.randint(0, len(operations) - 1)
        operation = operations[str(op + 1)]
        # lottery the operation new mode
        mode = random.randint(1, len(operation.modes))
        # if the operation have more the one mode, lottery while not choisen new mode
        while len(operation.modes) > 1 and mode == son["modes"][op]:
            mode = random.randint(1, len(operation.modes))

        son["modes"][op] = mode
        return son


    def data_mutation_process(self, son, preferences_function):
        """
        do motation on the new son.
        son: dictionary, son's data
        preferences_function: function, according to this function the gen created
        return: dictionary, the son after the motation, if was
        """
        resource_number = random.randint(0, len(son["data"]) - 1)
        # lottery an operation on which we will do the motation
        index = random.randint(1, len(son["data"][0]) - 1)
        # precede the choisen operation, only if its possible according to the preferences
        for i in range(index):
            if son["data"][resource_number][index] in preferences_function(son["data"][resource_number][:i]):
                son["data"][resource_number].insert(i, son["data"][resource_number].pop(index))

        return son


    # def mutation(self, son, operations, preferences_function):
    #     """
    #     do motation on the new son.
    #     son: dictionary, son's data
    #     operations: list of Operation, all operation data
    #     preferences_function: function, according to this function the gen created
    #     return: dictionary, the son after the motation, if was
    #     """
    #     # if the lottery number less then the motation chance, do the modes motation
    #     if random.random() <= self.mode_mutation:
    #         # lottery an operation on which we will do the motation
    #         op = random.randint(0, len(operations) - 1)
    #         operation = operations[str(op + 1)]
    #         # lottery the operation new mode
    #         mode = random.randint(1, len(operation.modes))
    #         # if the operation have more the one mode, lottery while not choisen new mode
    #         while len(operation.modes) > 1 and mode == son["modes"][op]:
    #             mode = random.randint(1, len(operation.modes))

    #         son["modes"][op] = mode

    #     # if the lottery number less then the motation chance, do the operations motation
    #     if random.random() <= self.data_mutation:
    #         resource_number = random.randint(0, len(son["data"]) - 1)
    #         # lottery an operation on which we will do the motation
    #         index = random.randint(1, len(son["data"][0]) - 1)
    #         # precede the choisen operation, only if its possible according to the preferences
    #         for i in range(index):
    #             if son["data"][resource_number][index] in preferences_function(son["data"][resource_number][:i]):
    #                 son["data"][resource_number].insert(i, son["data"][resource_number].pop(index))

    #     return son

    def complex_ageing_function(self, x):
        return abs(x-2) - 2


    def ageing_function(self, x):
        return x


    def next_generation_ageing_func(self, ageing):
        new_population = []
        new_solution_collected_data = []
        new_ageing = []
        # take the best |population_size| gens from the population
        for item_from_population, solution_data, item_from_ageing in sorted(zip(self.population, self.solution_collected_data, ageing), key=lambda pair: pair[0]["makespan"])[:self.population_size]:
            new_population.append(item_from_population)
            new_solution_collected_data.append(solution_data)
            new_ageing.append(item_from_ageing + 1)

        return new_population, new_solution_collected_data, new_ageing


    def next_generation_func(self):
        new_population = []
        new_solution_collected_data = []
        # take the best |population_size| gens from the population
        for item_from_population, solution_data in sorted(zip(self.population, self.solution_collected_data), key=lambda pair: pair[0]["makespan"])[:self.population_size]:
            new_population.append(item_from_population)
            new_solution_collected_data.append(solution_data)

        return new_population, new_solution_collected_data


    def is_cross_solution_in_best(self):
        best_solution = self.solution_collected_data[0]["value"]
        for p, solution_data in zip(self.population, self.solution_collected_data):
            if best_solution == solution_data["value"] and solution_data["cross_resources"]:
                return True

        return False


    # def calc_best_cross_solution(self, best_ga_solution, population, fitness_function):
    #     best_solution = best_ga_solution
    #     for son in population:
    #         solution = fitness_function(son["data"], son["modes"], True)["value"]
    #         best_solution = min(best_solution, solution)

    #     return best_solution / best_ga_solution

    def preper_son(self, son, job, fitness_function, solve_using_cross_solutions, lines, improved_method):
        new_son = self.mutation_process(son, job.operations, job.next_operations)
        if improved_method == "ga2s_select_all":
            solution = fitness_function(new_son["data"], new_son["modes"], True)
            solution_2 = fitness_function(new_son["data"], new_son["modes"], False)
            solution_data = solution if solution["value"] < solution_2["value"] else solution
        else:
            solution_data = fitness_function(new_son["data"], new_son["modes"], solve_using_cross_solutions)

        if solution_data["value"]:
            new_son["makespan"] = solution_data["value"]
        else:
            new_son, solution_data = self.__create_feasible_gen(job.operations, job.next_operations, fitness_function, lines, solve_using_cross_solutions)

        return new_son, solution_data


    def solve(self, job, name, fitness_function, solve_using_cross_solutions=True, lines=1, to_draw=None, greedy_solutions=[], improved_method=False):
        """
        use genetic algorithm on the problem and find the best UB.
        job: Job object, all problem data
        return: dictionary, {"value": best found ub, "generations": number of generations, "time": run time}
        """

        history_value = []
        history_cross = []
        self.exit = False
        self.reset_ga_params()
        ga_improved_generation = 0
        self.start = time.time()
        try:
            t = Timer(self.timeout, self.raiseTimeout)
            t.start()
            # create first population for the algorithm
            self.population, self.solution_collected_data = self.first_population(job.operations, job.next_operations, fitness_function, solve_using_cross_solutions, improved_method, lines)
            # population, solution_collected_data = self.next_generation_func(population, solution_collected_data)
            for greedy in greedy_solutions:
                solution_data_1 = fitness_function(greedy["data"], greedy["modes"], solve_using_cross_solutions)
                self.population.append(greedy)
                self.solution_collected_data.append(solution_data_1)

            self.population, self.solution_collected_data = self.next_generation_func()
            ga_min_val = self.population[0]["makespan"]
            if self.ageing:
                base_ageing = [-1] * self.population_size
                ageing = [0] * self.population_size
            # calcolate population score by the job fitness function
            # history.append(sum(fitness) / len(fitness))
            history_value.append(self.population[0]["makespan"])
            history_cross.append(self.is_cross_solution_in_best())
            for self.current_generation in range(1, self.generations + 1):
                # calcolate the probability of each gen to be selected as parent
                if self.ageing:
                    fitness = [p["makespan"] for p in self.population]
                    ageing_fitness = [f + (f * self.calc_ageing(a) / 10)  for f,a in zip(fitness, ageing)]
                    probability = [1 / item for item in ageing_fitness]
                else:
                    probability = [1 / p["makespan"] for p in self.population]

                F = sum(probability)
                weights = [item / F for item in probability]
                # create |population_size| new sons
                sons = []
                sons_solution_collected_data = []
                while len(sons) < self.population_size:
                    parent_1, parent_2 = random.choices(population=self.population, weights=weights, k=2)
                    son_1, son_2 = self.crossover(parent_1, parent_2)
                    son_1, solution_data_1 = self.preper_son(son_1, job, fitness_function, solve_using_cross_solutions, lines, improved_method)
                    son_2, solution_data_2 = self.preper_son(son_2, job, fitness_function, solve_using_cross_solutions, lines, improved_method)
                    sons.append(son_1)
                    sons.append(son_2)
                    sons_solution_collected_data.append(solution_data_1)
                    sons_solution_collected_data.append(solution_data_2)

                if improved_method == "ga2s_select_1":
                    son = sons[0]
                    solution_data = fitness_function(son["data"], son["modes"], solve_using_cross_solutions=True)
                    if solution_data["value"] < son["makespan"]:
                        son["makespan"] = solution_data["value"]
                        sons_solution_collected_data[0] = solution_data

                if improved_method == "ga2s_select_quarter":
                    index_to_improve = random.sample(range(len(sons)), int(len(sons) / 4))
                    for index in index_to_improve:
                        son = sons[index]
                        solution_data = fitness_function(son["data"], son["modes"], solve_using_cross_solutions=True)
                        if solution_data["value"] < son["makespan"]:
                            son["makespan"] = solution_data["value"]
                            sons_solution_collected_data[index] = solution_data

                self.population += sons
                self.solution_collected_data += sons_solution_collected_data

                if self.ageing:
                    ageing += base_ageing
                    self.population, self.solution_collected_data, ageing = self.next_generation(ageing)
                else:
                    self.population, self.solution_collected_data = self.next_generation()

                if self.changed_mutation:
                    if self.population[0]["makespan"] == self.population[int(len(self.population) / 2)]["makespan"]:
                        self.mode_mutation *= 2
                        self.data_mutation *= 2
                    else:
                        self.mode_mutation = max(self.base_mode_mutation, self.mode_mutation / 2)
                        self.data_mutation = max(self.base_data_mutation, self.data_mutation / 2)
                # history.append(sum(fitness) / float(len(fitness)))
                history_value.append(self.population[0]["makespan"])
                history_cross.append(self.is_cross_solution_in_best())
                if self.population[0]["makespan"] < ga_min_val:
                    ga_min_val = self.population[0]["makespan"]
                    ga_improved_generation = self.current_generation

            run_time = time.time() - self.start
            try:
                with open("ga.csv", "a+") as f:
                    writer = csv.writer(f)
                    writer.writerow(["{}_{}_{}".format(job.problem_id, name, improved_method)] + history_value)
                    writer.writerow(["{}_{}_{}_cross".format(job.problem_id, name, improved_method)] + history_cross)
            except Exception as e:
                print(e)
                pass

            # return the solution value, number of generations, the taken time and the solution draw data
            if to_draw:
                solution_draw_data = self.solution_collected_data[0]["to_draw"]
                # modify the solution title to the GA run time
                solution_draw_data["title"] = "solution in {:.10f} sec\ncreated nodes = 0, max queue size = 0".format(run_time)
            else:
                solution_draw_data=None

            # cross_vs_not_cross = self.calc_best_cross_solution(population[0]["makespan"], population, fitness_function)
            # with open("cross_vs_not.csv", "a+") as f:
            #     f.write("{}_{}, {}\n".format(job.problem_id, name, cross_vs_not_cross))

        except InfeasibleException as e:
            print(e)
            solution_draw_data=None
            # population = [{"modes": -1, "data": -1, "makespan": float('inf')}]
            # solution_collected_data = [{"value": float('inf'), "cross_solutions": False, "cross_resources": 0}]
            # generation = -1
            if self.feasibles_counter != 0:
                run_time =  (time.time() - self.start) / self.feasibles_counter * self.min_solutions_to_calculate
            else:
                run_time = (time.time() - self.start) * self.min_solutions_to_calculate

        finally:
            t.cancel()

        cross_best_solution = self.is_cross_solution_in_best()
        feasibles = (self.feasibles_counter / (self.feasibles_counter + self.infeasibles_counter)) * 100
        if improved_method == "one":
            greedy_solutions += self.population
            return self.solve(job, name, fitness_function=fitness_function, solve_using_cross_solutions=True, lines=lines, to_draw=True, greedy_solutions=greedy_solutions, improved_method="new")

        print("{}_{}: solve end at {}\ncross_best_solution = {}".format(job.problem_id, name, time.strftime("%H:%M:%S", time.localtime()), cross_best_solution))

        if improved_method in ["ga2s_final", "ga2s_select_1"]:
            step_time = time.time()
            solution_collected_data_cross = []
            for son, data in zip(self.population, self.solution_collected_data):
                solution_data = fitness_function(son["data"], son["modes"], solve_using_cross_solutions=True)
                if solution_data["value"] < son["makespan"]:
                    son["makespan"] = solution_data["value"]
                    solution_collected_data_cross.append(solution_data)
                else:
                    solution_collected_data_cross.append(data)
                
            cross_population, solution_collected_data_cross = self.next_generation(self.population, solution_collected_data_cross)
            cross_run_time = run_time + time.time() - step_time
            cross_best_solution = self.is_cross_solution_in_best(cross_population, solution_collected_data_cross)
            return {"value": solution_collected_data_cross[0]["value"], "cross_value": solution_collected_data_cross[0]["value"],
                "generations": self.current_generation, "time": run_time, "cross_time": cross_run_time, "to_draw": solution_draw_data, 
                "feasibles": feasibles, "cross_resources": solution_collected_data_cross[0]["cross_resources"], 
                "cross_best_solution": cross_best_solution, "improved_generation": ga_improved_generation}
        
        return {"value": self.solution_collected_data[0]["value"], "generations": self.current_generation, 
                "time": run_time, "to_draw": solution_draw_data, 
                "feasibles": feasibles, "cross_resources": self.solution_collected_data[0]["cross_resources"], 
                "cross_best_solution": cross_best_solution, "improved_generation": ga_improved_generation,
                "origin": self.population[0]["origin"]}