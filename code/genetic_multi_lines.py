import random
import time
import csv

class GA_multi_lines:
    """
    this class present a genetic algorithm.
    this class resive fitness function and data about the genetic options:
        population_size, mutation and number of generations
    by the given data, the algorithm try to solve the problem
    """

    def __init__(self, generations = 50, population_size=50, mode_mutation=0.04, res_mutation=0.04, operations_pref_len=[]):
        self.generations = generations
        self.population_size = population_size
        self.mode_mutation = mode_mutation
        self.res_mutation = res_mutation
        self.infeasibles_counter = 0
        self.feasibles_counter = 0
        self.cross_solutions = 0
        self.operations_pref_len = operations_pref_len


    def first_population(self, operations, preferences_function, resources_number, fitness_function):
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
            gen, solution = self.create_feasible_gen(operations, preferences_function, resources_number, fitness_function)
            population.append(gen)
            fitness.append(solution)
            print("+1... population =", self.population_size)

        return population, fitness


    def check_cross_solution(self, resources_list, modes_list, operations_list):
        operations_coef = {str(pos):set() for pos in range(1, len(resources_list[0]) + 1)}
        copy_resources_list = [resources[:] for resources in resources_list]
        for res_number, operations in enumerate(copy_resources_list, start=1):
            index = 0
            # remove all not needed resource from the resources list
            while index < len(operations):
                needed_resource = False
                mode_resorces = operations_list[operations[index]].get_mode_by_name(str(modes_list[int(operations[index]) - 1])).resources
                needed_resource = any(str(res_number) == resource.number for resource in mode_resorces)
                if not needed_resource:
                    operations.remove(operations[index])
                # if the resource is used, check next resource and add 1 to the number of used resources
                else:
                    index += 1

        for operations in copy_resources_list:
            for pos, op in enumerate(operations[:-1], start=1):
                follow_operations = set(operations[pos:])
                for follow_op in follow_operations:
                    if op in operations_coef[follow_op]:
                        return True
                else:
                    operations_coef[str(op)].update(follow_operations)
        
        return False


    def create_feasible_gen(self, operations, preferences_function, resources_number, fitness_function):
        while True:
            modes = []
            resources = [[] for i in range(resources_number)]
            # for each operation randomly select mode
            for op in operations.values():
                modes.append(random.randint(1, len(op.modes)))

            # the preferences_function return all operation that can be start after all already done operations
            # according to the preferences limits
            for resource in range(resources_number):
                possible_resources = preferences_function(resources[resource])
                while possible_resources:
                    # randomly choise the next operation from all available operations
                    res = random.choice(possible_resources)
                    resources[resource].append(res)
                    possible_resources = preferences_function(resources[resource])

            solution = fitness_function(resources, modes).bellman_ford_LB(0, len(operations) + 1, self.operations_pref_len)
            if solution:
                # for each gen, save the choisen modes and the operations order
                self.feasibles_counter += 1
                if self.check_cross_solution(resources, modes, operations):
                    self.cross_solutions += 1
                return {"modes": modes, "resources": resources}, solution

            else:
                self.infeasibles_counter += 1
                if self.infeasibles_counter % 1000000 == 0:
                    print("infeasibles_counter =", self.infeasibles_counter)
                    print("feasibles_counter =", self.feasibles_counter, "\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")



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
        resources = [[] for i in range(len(parent_1["resources"]))]
        for res_number, res in enumerate(parent_1["resources"]):
            resources[res_number] = res[0:res_index]
            for p2_res in res:
                if p2_res not in resources[res_number]:
                    resources[res_number].append(p2_res)

        # return the new son
        return {"modes": modes, "resources": resources}


    def crossover(self, parent_1, parent_2):
        """
        crossover between two parents to create 2 new sons.
        parent_1: dictionary, gen data
        parent_2: dictionary, gen data
        return: 2 dictionary, 2 new sons
        """
        # lattery the cross index, one for the modes and another for the operations
        max_index = len(parent_1["modes"]) - 2
        mode_index = random.randint(1, max_index)
        res_index = random.randint(1, max_index)
        # create 2 new sons
        son_1 = self.__crossover(parent_1, parent_2, mode_index, res_index)
        son_2 = self.__crossover(parent_2, parent_1, mode_index, res_index)
        return son_1, son_2


    def mutation(self, son, operations, preferences_function):
        """
        do motation on the new son.
        son: dictionary, son's data
        operations: list of Operation, all operation data
        preferences_function: function, according to this function the gen created
        return: dictionary, the son after the motation, if was
        """
        # if the lottery number less then the motation chance, do the modes motation
        if random.random() <= self.mode_mutation:
            # lottery an operation on which we will do the motation
            op = random.randint(0, len(operations) - 1)
            operation = operations[str(op + 1)]
            # lottery the operation new mode
            mode = random.randint(1, len(operation.modes))
            # if the operation have more the one mode, lottery while not choisen new mode
            while len(operation.modes) > 1 and mode == son["modes"][op]:
                mode = random.randint(1, len(operation.modes))

            son["modes"][op] = mode

        # if the lottery number less then the motation chance, do the operations motation
        if random.random() <= self.res_mutation:
            resource_number = random.randint(1, len(son["resources"]) - 1)
            # lottery an operation on which we will do the motation
            index = random.randint(1, len(son["resources"][0]) - 1)
            # precede the choisen operation, only if its possible according to the preferences
            for i in range(index):
                if son["resources"][resource_number][index] in preferences_function(son["resources"][resource_number][:i]):
                    son["resources"][resource_number].insert(i, son["resources"][resource_number].pop(index))

        return son


    def solve(self, job):
        """
        use genetic algorithm on the problem and find the best UB.
        job: Job object, all problem data
        return: dictionary, {"value": best found ub, "generations": number of generations, "time": run time}
        """
        history = []
        start = time.time()
        # create first population for the algorithm
        population, fitness = self.first_population(job.operations, job.next_operations, len(job.resources), job.add_resources_to_bellman_ford_graph)
        # calcolate population score by the job fitness function
        history.append(sum(fitness) / len(fitness))
        for generation in range(self.generations):
            print("generation:", generation)
            # calcolate the probability of each gen to be selected as parent
            probability = [1 / item for item in fitness]
            F = sum(probability)
            weights = [item / F for item in probability]
            # create |population_size| new sons
            sons = []
            while len(sons) < self.population_size:
                parent_1, parent_2 = random.choices(population=population, weights=weights, k=2)
                son_1, son_2 = self.crossover(parent_1, parent_2)
                son_1 = self.mutation(son_1, job.operations, job.next_operations)
                son_2 = self.mutation(son_2, job.operations, job.next_operations)
                solution_1 = job.add_resources_to_bellman_ford_graph(son_1["resources"], son_1["modes"]).bellman_ford_LB(0, len(job.operations) + 1, self.operations_pref_len)
                if not solution_1:
                    son_1, solution_1 = self.create_feasible_gen(job.operations, job.next_operations, len(job.resources), job.add_resources_to_bellman_ford_graph)

                solution_2 = job.add_resources_to_bellman_ford_graph(son_2["resources"], son_2["modes"]).bellman_ford_LB(0, len(job.operations) + 1, self.operations_pref_len)
                if not solution_2:
                    son_2, solution_2 = self.create_feasible_gen(job.operations, job.next_operations, len(job.resources), job.add_resources_to_bellman_ford_graph)
                
                sons.append(son_1)
                sons.append(son_2)
                fitness.append(solution_1)
                fitness.append(solution_2)

            population += sons
            new_population = []
            new_fitness = []
            # take the best |population_size| gens from the population
            for item_from_fitness, item_from_population in sorted(zip(fitness, population), key=lambda pair: pair[0]):
                new_population.append(item_from_population)
                new_fitness.append(item_from_fitness)

            population = new_population[:self.population_size]
            fitness = new_fitness[:self.population_size]
            history.append(sum(fitness) / float(len(fitness)))
            # we may stack in local minimom, try to escape by incrise the mutation chance
            # if fitness[0] == fitness[-1]:
            #     break

        run_time = time.time() - start
        with open("ga.csv", "a+") as f:
            writer = csv.writer(f)
            writer.writerow(history)

        # return the solution value, number of generations, the taken time and the solution draw data
        # solution_draw_data = job.find_ub_ga(population[0]["operations"], population[0]["modes"])["to_draw"]
        # modify the solution title to the GA run time
        # solution_draw_data["title"] = "solution in {:.10f} sec\ncreated nodes = 0, max queue size = 0".format(run_time)
        if self.check_cross_solution(population[0]["resources"], population[0]["modes"], job.operations):
            print("@@@@@@@@@best_solution_have_cross_resources@@@@@@@@@@@")
        feasibles = (self.feasibles_counter / (self.feasibles_counter + self.infeasibles_counter)) * 100
        return {"value": fitness[0], "generations": generation, "time": run_time, "to_draw": None, "feasibles": feasibles, "cross_solutions": self.cross_solutions}
