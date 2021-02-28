import random
import time
import csv
from threading import Timer
from datetime import datetime


class InfeasibleException(Exception):
    def __init__(self, infeasibles_counter, feasibles_counter, run_time):
        self.feasibles = feasibles_counter
        self.infeasibles = infeasibles_counter
        self.run_time = run_time

    def __str__(self):
        return str("InfeasibleException:\nafter = {}s, infeasibles_counter = {}, feasibles_counter = {}").format(self.run_time, self.infeasibles, self.feasibles)

class GA:

    """
    this class present a genetic algorithm.
    this class resive fitness function and data about the genetic options:
        population_size, mutation and number of generations
    by the given data, the algorithm try to solve the problem
    """

    def __init__(self, generations = 50, population_size=16, mode_mutation=0.04, data_mutation=0.04, solve_using_cross_solutions=True, check_cross_solution=None, timeout=None, multi_times=False, changed_mutation=False, ageing=False, complex_ageing=False):
        self.generations = generations
        self.population_size = population_size
        self.mode_mutation = self.base_mode_mutation = mode_mutation
        self.data_mutation = self.base_data_mutation = data_mutation
        self.timeout = timeout
        self.multi_times = multi_times
        self.changed_mutation = changed_mutation
        self.ageing = ageing
        self.infeasibles_counter = 0
        self.feasibles_counter = 0
        self.cross_solutions = 0
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
        self.solve_using_cross_solutions = solve_using_cross_solutions
        if check_cross_solution:
            self.check_cross_solution = check_cross_solution
        else:
            self.check_cross_solution = self.check_cross_solution_func


    def reset_ga_params(self):
        self.mode_mutation = self.base_mode_mutation
        self.data_mutation = self.base_data_mutation


    def check_cross_solution_func(self, foo, bar):
        return False


    def raiseTimeout(self):
        self.exit = True


    def first_population(self, operations, preferences_function, fitness_function, resources_number=1):
        """
        create the first population with the operation and preferences data
        operations: list of Operation, all operation data
        preferences_function: function, according to this function the gen created
        return: list of dictionary, [{"modes": number, "operations": number}]
        """
        self.infeasibles_counter = 0
        self.feasibles_counter = 0
        self.cross_solutions = 0
        population = []
        fitness = []
        for _ in range(self.population_size):
            gen, solution = self.__create_feasible_gen(operations, preferences_function, fitness_function, resources_number)
            population.append(gen)
            fitness.append(solution)

        return population, fitness


    def __create_feasible_gen(self, operations, preferences_function, fitness_function, resources_number):
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

            solution = fitness_function(data, modes, self.solve_using_cross_solutions)
            if solution["value"]:
                # for each gen, save the choisen modes and the operations order
                self.feasibles_counter += 1
                if self.check_cross_solution(data, modes):
                    self.cross_solutions += 1
                return {"modes": modes, "data": data}, solution["value"]

            else:
                self.infeasibles_counter += 1
                if self.infeasibles_counter > 10000 and self.feasibles_counter / self.infeasibles_counter < 0.001:
                    raise InfeasibleException(self.infeasibles_counter, self.feasibles_counter, time.time() - self.start)

        raise InfeasibleException(self.infeasibles_counter, self.feasibles_counter, time.time() - self.start)


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
        for res_number, res in enumerate(parent_1["data"]):
            data[res_number] = res[0:res_index]
            for p2_res in res:
                if p2_res not in data[res_number]:
                    data[res_number].append(p2_res)

        # return the new son
        return {"modes": modes, "data": data}


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


    def next_generation_ageing_func(self, population, fitness, ageing):
        new_population = []
        new_fitness = []
        new_ageing = []
        # take the best |population_size| gens from the population
        for item_from_fitness, item_from_population, item_from_ageing in sorted(zip(fitness, population, ageing), key=lambda pair: pair[0]):
            new_population.append(item_from_population)
            new_fitness.append(item_from_fitness)
            new_ageing.append(item_from_ageing + 1)

        return new_population[:self.population_size], new_fitness[:self.population_size], new_ageing[:self.population_size]


    def next_generation_func(self, population, fitness):
        new_population = []
        new_fitness = []
        # take the best |population_size| gens from the population
        for item_from_fitness, item_from_population in sorted(zip(fitness, population), key=lambda pair: pair[0]):
            new_population.append(item_from_population)
            new_fitness.append(item_from_fitness)

        return new_population[:self.population_size], new_fitness[:self.population_size]
        

    def solve(self, job, fitness_function, lines=1, to_draw=None):
        """
        use genetic algorithm on the problem and find the best UB.
        job: Job object, all problem data
        return: dictionary, {"value": best found ub, "generations": number of generations, "time": run time}
        """
        history = []
        self.exit = False
        self.reset_ga_params()
        self.start = time.time()
        try:
            t = Timer(self.timeout, self.raiseTimeout)
            t.start()
            # create first population for the algorithm
            population, fitness = self.first_population(job.operations, job.next_operations, fitness_function, lines)
            if self.ageing:
                base_ageing = [-1] * self.population_size
                ageing = [0] * self.population_size
            # calcolate population score by the job fitness function
            # history.append(sum(fitness) / len(fitness))
            history.append(fitness[0])
            for generation in range(self.generations):
                # calcolate the probability of each gen to be selected as parent
                if self.ageing:
                    ageing_fitness = [f + (f * self.calc_ageing(a) / 10)  for f,a in zip(fitness, ageing)]
                    probability = [1 / item for item in ageing_fitness]
                else:
                    probability = [1 / item for item in fitness]

                F = sum(probability)
                weights = [item / F for item in probability]
                # create |population_size| new sons
                sons = []
                while len(sons) < self.population_size:
                    parent_1, parent_2 = random.choices(population=population, weights=weights, k=2)
                    son_1, son_2 = self.crossover(parent_1, parent_2)
                    son_1 = self.mutation_process(son_1, job.operations, job.next_operations)
                    son_2 = self.mutation_process(son_2, job.operations, job.next_operations)
                    solution_1 = fitness_function(son_1["data"], son_1["modes"], self.solve_using_cross_solutions)["value"]
                    if not solution_1:
                        son_1, solution_1 = self.__create_feasible_gen(job.operations, job.next_operations, fitness_function, lines)

                    solution_2 = fitness_function(son_2["data"], son_2["modes"], self.solve_using_cross_solutions)["value"]
                    if not solution_2:
                        son_2, solution_2 = self.__create_feasible_gen(job.operations, job.next_operations, fitness_function, lines)

                    sons.append(son_1)
                    sons.append(son_2)
                    fitness.append(solution_1)
                    fitness.append(solution_2)

                population += sons

                if self.ageing:
                    ageing += base_ageing
                    population, fitness, ageing = self.next_generation(population, fitness, ageing)
                else:
                    population, fitness = self.next_generation(population, fitness)

                if self.changed_mutation:
                    if fitness[0] == fitness[int(len(fitness) / 2)]:
                        self.mode_mutation *= 2
                        self.data_mutation *= 2
                    else:
                        self.mode_mutation = max(self.base_mode_mutation, self.mode_mutation / 2)
                        self.data_mutation = max(self.base_data_mutation, self.data_mutation / 2)
                # history.append(sum(fitness) / float(len(fitness)))
                history.append(fitness[0])

            run_time = time.time() - self.start
            with open("ga.csv", "a+") as f:
                writer = csv.writer(f)
                writer.writerow(history)

            # return the solution value, number of generations, the taken time and the solution draw data
            if to_draw:
                solution_draw_data = fitness_function(population[0]["data"], population[0]["modes"], self.solve_using_cross_solutions)["to_draw"]
                # modify the solution title to the GA run time
                solution_draw_data["title"] = "solution in {:.10f} sec\ncreated nodes = 0, max queue size = 0".format(run_time)
            else:
                solution_draw_data=None

        except InfeasibleException as e:
            print(e)
            solution_draw_data=None
            self.check_cross_solution = self.check_cross_solution_func
            fitness = [float('inf')]
            population = [{"modes": -1, "data": -1}]
            generation = -1
            if self.feasibles_counter != 0:
                run_time =  (time.time() - self.start) / self.feasibles_counter * self.min_solutions_to_calculate
            else:
                run_time = (time.time() - self.start) * self.min_solutions_to_calculate

        finally:
            t.cancel()

        print("GA solve end at {}".format(time.strftime("%H:%M:%S", time.localtime())))
        cross_best_solution = self.check_cross_solution(population[0]["data"], population[0]["modes"])
        feasibles = (self.feasibles_counter / (self.feasibles_counter + self.infeasibles_counter)) * 100
        return {"value": fitness[0], "generations": generation, 
                "time": run_time, "to_draw": solution_draw_data, 
                "feasibles": feasibles, "cross_solutions": self.cross_solutions, 
                "cross_best_solution": cross_best_solution}