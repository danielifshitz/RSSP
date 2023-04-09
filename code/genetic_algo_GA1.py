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

class GA_1:

    """
    this class present a genetic algorithm.
    this class resive fitness function and data about the genetic options:
        population_size, mutation and number of generations
    by the given data, the algorithm try to solve the problem
    """

    def __init__(self, generations=50, population_size=16, mode_mutation=0.04, data_mutation=0.04, timeout=None):
        self.generations = generations
        self.current_generation = 0
        self.population_size = population_size
        self.mode_mutation = self.base_mode_mutation = mode_mutation
        self.data_mutation = self.base_data_mutation = data_mutation
        self.timeout = timeout
        self.infeasibles_counter = 0
        self.feasibles_counter = 0
        self.infeasibles_cross = 0
        self.feasibles_cross = 0
        self.exit = False
        self.fix_gen = self.__fix_gen_dummy
        self.next_generation = self.next_generation_func
        self.min_solutions_to_calculate = (generations + 1) * population_size
        self.solve_using_cross_solutions = True


    def reset_ga_params(self):
        self.mode_mutation = self.base_mode_mutation
        self.data_mutation = self.base_data_mutation
        

    def raiseTimeout(self):
        self.exit = True


    def fitness_function(self, fitness, gen, resources_number):
        modes, data = self.__get_data_modes(gen, resources_number)
        solution = fitness(data, modes, self.solve_using_cross_solutions)
        return solution


    def first_population(self, operations, preferences_function, fitness_function, resources_number):
        """
        create the first population with the operation and preferences data
        operations: list of Operation, all operation data
        preferences_function: function, according to this function the gen created
        return: list of dictionary, [{"modes": number, "operations": number}]
        """
        self.infeasibles_counter = 0
        self.feasibles_counter = 0
        self.infeasibles_cross = 0
        self.feasibles_cross = 0
        self.current_generation = 0
        self.population = []
        self.solution_collected_data = []
        for _ in range(self.population_size):
            gen, solution_data = self.__create_feasible_gen(operations, preferences_function, fitness_function, resources_number)
            self.population.append(gen)
            self.solution_collected_data.append(solution_data)

        return self.population, self.solution_collected_data


    def __create_feasible_gen(self, operations, preferences_function, fitness_function, resources_number):
        while not self.exit:
            insert = 1
            gen = {i:[] for i in range(1, len(operations) + 1)}
            # modes = []
            # data = [[] for i in range(resources_number)]
            # for each operation randomly select mode
            for i, op in enumerate(operations.values(), start=1):
                # modes.append(random.randint(1, len(op.modes)))
                selected_mode = str(random.randint(1, len(op.modes)))
                for mode in op.modes:
                    m = {"selected": False, "resources": {}, "number": mode.mode_number}
                    if selected_mode == mode.mode_number:
                        m["selected"] = True

                    for resource in mode.resources:
                        m["resources"][resource.number] = insert

                    gen[i].append(m)

            gen = self.__fix_gen_if_needed(gen, operations, preferences_function, resources_number)

            solution = self.fitness_function(fitness_function, gen, resources_number)
            if solution["value"]:
                # for each gen, save the choisen modes and the operations order
                self.feasibles_counter += 1
                return {"gen": gen, "makespan": solution["value"], "cross_resources": solution["cross_resources"]}, solution

            else:
                self.infeasibles_counter += 1
                if self.infeasibles_counter > 10000 and self.feasibles_counter / self.infeasibles_counter < 0.001:
                    self.solution_collected_data.append({"value": float('inf'), "cross_resources": -1})
                    raise InfeasibleException(self.infeasibles_counter, self.feasibles_counter, time.time() - self.start, self.solution_collected_data[0]["value"])

        self.solution_collected_data.append({"value": float('inf'), "cross_resources": -1})
        raise InfeasibleException(self.infeasibles_counter, self.feasibles_counter, time.time() - self.start, self.solution_collected_data[0]["value"])


    def __fix_gen_if_needed(self, gen, operations, preferences_function, resources_number):
        if self._if_problem(gen, resources_number):
            gen = self.fix_gen(gen, operations, preferences_function, resources_number)
            assert not self._if_problem(gen, resources_number)

        return gen


    def _if_problem(self, gen, resources_number):
        resources = {str(i):[] for i in range(1, resources_number + 1)}
        for op in gen.values():
            selected = False
            for mode in op:
                if mode["selected"] is True:
                    selected = True
                    for res_number, res_order in mode["resources"].items():
                        resources[res_number].append(res_order)
            
            assert selected, "no selected mode! exiting"

        for res_order in resources.values():
            if len(res_order) != len(set(res_order)):
                return True
            
            for i in range(1, len(res_order) + 1):
                if i not in res_order:
                    return True

        return False


    def __fix_gen_dummy(self, gen, operations, preferences_function, resources_number):
        return gen


    def __fix_gen_operations(self, gen, operations, preferences_function, resources_number):
        ops = []
        resources = {str(i):1 for i in range(1, resources_number + 1)}
        while len(ops) < len(operations):
            possible_operations = preferences_function(ops)
            bad_ops = []
            good_ops = []
            for op_number in possible_operations:
                op = gen[int(op_number)]
                for mode in op:
                    if mode["selected"] is True:
                        for res, order in mode["resources"].items():
                            if order != resources[res]:
                                bad_ops.append(op_number)
                                break
                        else:
                            good_ops.append(op_number)

            if good_ops:
                op_number = random.choice(good_ops)
                op = gen[int(op_number)]
                for mode in op:
                    if mode["selected"] is True:
                        for res in mode["resources"].keys():
                            resources[res] += 1
                        
                        break
            else:
                op_number = random.choice(bad_ops)
                op = gen[int(op_number)]
                for mode in op:
                    if mode["selected"] is True:
                        for res in mode["resources"].keys():
                            mode["resources"][res] = resources[res]
                            resources[res] += 1

                        break

            ops.append(op_number)
        
        return gen


    def __fix_gen_resources(self, gen, operations, preferences_function, resources_number):
        for r in range(1, resources_number + 1):
            r = str(r)
            ops = []
            resource_order = 1
            while len(ops) < len(operations):
                possible_operations = preferences_function(ops)
                bad_ops = []
                good_ops = []
                for op_number in possible_operations:
                    op = gen[int(op_number)]
                    for mode in op:
                        if mode["selected"] is True:
                            if r in mode["resources"]:
                                if mode["resources"][r] == resource_order:
                                    good_ops.append(op_number)
                                else:
                                    bad_ops.append(op_number)

                                break
                                

                if good_ops:
                    op_number = random.choice(good_ops)
                    resource_order += 1

                elif bad_ops:
                    op_number = random.choice(bad_ops)
                    op = gen[int(op_number)]
                    for mode in op:
                        if mode["selected"] is True:
                            mode["resources"][r] = resource_order
                            resource_order += 1
                            break

                ops.append(op_number)
            
        return gen


    def __get_data_modes(self, gen, resources_number):
        modes_list = []
        resources = [[] for _ in range(resources_number)]
        for op, modes in gen.items():
            for mode in modes:
                if mode["selected"] is True:
                    modes_list.append(int(mode["number"]))
                    for res, order in mode["resources"].items():
                        while len(resources[int(res) - 1]) < order:
                            resources[int(res) - 1].append(0)

                        resources[int(res) - 1][order - 1] = str(op)
                    
                    break

        return modes_list, resources


    def __crossover(self, parent_1, parent_2, res_index):
        """
        crossover between two parents to create 2 new sons.
        parent_1: dictionary, gen data
        parent_2: dictionary, gen data
        mode_index: number, index for the modes crossover
        op_index: number, index for the operations crossover
        return: dictionary, new son
        """
        # operation crossover
        # take from 0 to index-1 from the first parent all not selected operations from the second parent
        gen = {}
        for i in range(1, res_index + 1):
            gen[i] = parent_1["gen"][i]

        for i in range(res_index + 1, len(parent_2["gen"]) + 1):
            gen[i] = parent_2["gen"][i]

        # return the new son
        return {"gen": gen}


    def crossover(self, parent_1, parent_2):
        """
        crossover between two parents to create 2 new sons.
        parent_1: dictionary, gen data
        parent_2: dictionary, gen data
        return: 2 dictionary, 2 new sons
        """
        # lattery the cross index, one for the modes and another for the operations
        max_index = len(parent_1["gen"]) - 1
        res_index = random.randint(1, max_index)
        # create 2 new sons
        son_1 = self.__crossover(parent_1, parent_2, res_index)
        son_2 = self.__crossover(parent_2, parent_1, res_index)
        return son_1, son_2


    def mutation_process(self, son):
        # if the lottery number less then the motation chance, do the modes motation
        if random.random() <= self.mode_mutation:
            op = random.randint(1, len(son["gen"]))
            done = False
            while len(son["gen"][op]) > 1 and not done:
                selected_mode = str(random.randint(0, len(son["gen"][op]) - 1))
                for mode in son["gen"][op]:
                    if mode["number"] == selected_mode and mode["selected"] is False:
                        mode["selected"] = True
                        done = True
                    elif mode["number"] == selected_mode: # the same mode selected
                        break
                    else:
                        mode["selected"] = False
        return son


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
        for solution_data in self.solution_collected_data:
            if best_solution == solution_data["value"] and solution_data["cross_resources"]:
                return True

        return False


    def preper_son(self, son, job, fitness_function, resources_number):
        new_son = self.mutation_process(son)
        new_son["gen"] = self.__fix_gen_if_needed(new_son["gen"], job.operations, job.next_operations, resources_number)
        solution_data = self.fitness_function(fitness_function, new_son["gen"], resources_number)
        if solution_data["value"]:
            new_son["makespan"] = solution_data["value"]
            self.feasibles_cross += 1
        else:
            new_son, solution_data = self.__create_feasible_gen(job.operations, job.next_operations, fitness_function, resources_number)
            self.infeasibles_cross += 1

        return new_son, solution_data


    def solve(self, job, name, fitness_function, resources_number, improved_method):
        """
        use genetic algorithm on the problem and find the best UB.
        job: Job object, all problem data
        return: dictionary, {"value": best found ub, "generations": number of generations, "time": run time}
        """
        history_value = []
        history_cross = []
        self.exit = False
        ga_improved_generation = 0
        generation = -1
        if improved_method == "ga1_op":
            self.fix_gen = self.__fix_gen_operations
        elif improved_method == "ga1_res":
            self.fix_gen = self.__fix_gen_resources

        self.reset_ga_params()
        self.start = time.time()
        try:
            t = Timer(self.timeout, self.raiseTimeout)
            t.start()
            # create first population for the algorithm
            self.population, self.solution_collected_data = self.first_population(job.operations, job.next_operations, fitness_function, resources_number)
            self.population, self.solution_collected_data = self.next_generation_func()
            ga_min_val = self.population[0]["makespan"]
            # calcolate population score by the job fitness function
            # history.append(sum(fitness) / len(fitness))
            history_value.append(self.population[0]["makespan"])
            history_cross.append(self.is_cross_solution_in_best())
            for self.current_generation in range(self.generations):
                # calcolate the probability of each gen to be selected as parent
                probability = [1 / p["makespan"] for p in self.population]
                F = sum(probability)
                weights = [item / F for item in probability]
                # create |population_size| new sons
                sons = []
                sons_solution_collected_data = []
                while len(sons) < self.population_size:
                    parent_1, parent_2 = random.choices(population=self.population, weights=weights, k=2)
                    son_1, son_2 = self.crossover(parent_1, parent_2)
                    son_1, solution_data_1 = self.preper_son(son_1, job, fitness_function, resources_number)
                    son_2, solution_data_2 = self.preper_son(son_2, job, fitness_function, resources_number)
                    sons.append(son_1)
                    sons.append(son_2)
                    sons_solution_collected_data.append(solution_data_1)
                    sons_solution_collected_data.append(solution_data_2)

                self.population += sons
                self.solution_collected_data += sons_solution_collected_data
                self.population, self.solution_collected_data = self.next_generation_func()
                history_value.append(self.population[0]["makespan"])
                history_cross.append(self.is_cross_solution_in_best())
                if self.population[0]["makespan"] < ga_min_val:
                    ga_min_val = self.population[0]["makespan"]
                    ga_improved_generation = self.current_generation

            run_time = time.time() - self.start
            with open("ga.csv", "a+") as f:
                writer = csv.writer(f)
                writer.writerow(["{}_{}_{}".format(job.problem_id, name, improved_method)] + history_value)
                writer.writerow(["{}_{}_{}_cross".format(job.problem_id, name, improved_method)] + history_cross)

            solution_draw_data=None

        except InfeasibleException as e:
            print(e)
            solution_draw_data=None
            # population = [{"gen": -1, "makespan": float('inf')}]
            # solution_collected_data = [{"value": float('inf'), "cross_solutions": False, "cross_resources": 0}]
            if self.feasibles_counter != 0:
                run_time =  (time.time() - self.start) / self.feasibles_counter * self.min_solutions_to_calculate
            else:
                run_time = (time.time() - self.start) * self.min_solutions_to_calculate

        finally:
            t.cancel()

        cross_best_solution = self.is_cross_solution_in_best()
        if improved_method == "ga1_op":
            feasibles = (self.feasibles_cross / (self.feasibles_cross + self.infeasibles_cross)) * 100
        elif improved_method == "ga1_res":
            feasibles = (self.feasibles_counter / (self.feasibles_counter + self.infeasibles_counter)) * 100
        
        print("{}_{}: solve end at {}\ncross_best_solution = {}".format(job.problem_id, name, time.strftime("%H:%M:%S", time.localtime()), cross_best_solution))
        print(f"feasibles = {feasibles}")
        
        return {"value": self.solution_collected_data[0]["value"], "generations": self.current_generation, 
                "time": run_time, "to_draw": solution_draw_data, 
                "feasibles": feasibles, "cross_resources": self.solution_collected_data[0]["cross_resources"], 
                "cross_best_solution": cross_best_solution, "improved_generation": ga_improved_generation}