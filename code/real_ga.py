import random
import time
import csv

class GA2:

    """
    this class present a genetic algorithm.
    this class resive fitness function and data about the genetic options:
        population_size, mutation and number of generations
    by the given data, the algorithm try to solve the problem
    """

    def __init__(self, generations = 50, population_size=50, mode_mutation=0.04, op_mutation=0.04):
        self.generations = generations
        self.population_size = population_size
        self.mode_mutation = mode_mutation
        self.op_mutation = op_mutation


    def first_population(self, operations, preferences_function):
        """
        create the first population with the operation and preferences data
        operations: list of Operation, all operation data
        preferences_function: function, according to this function the gen created
        return: list of dictionary, [{"modes": number, "operations": number}]
        """
        population = []
        for _ in range(self.population_size):
            modes = []
            preferences = []
            # for each operation randomly select mode
            for op in operations.values():
                modes.append(random.randint(1, len(op.modes)))

            # the preferences_function return all operation that can be start after all already done operations
            # according to the preferences limits
            possible_operations = preferences_function([])
            while possible_operations:
                # rendomly choise the next operation from all available operations
                preferences.append(random.choice(possible_operations))
                possible_operations = preferences_function(preferences)

            # for each gen, save the choisen modes and the operations order
            population.append({"modes": modes, "operations": preferences})

        return population


    def __crossover(self, parent_1, parent_2, mode_index, op_index):
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
        operations = parent_1["operations"][0:op_index]
        for op in parent_2["operations"]:
            if op not in operations:
                operations.append(op)

        # return the new son
        return {"modes": modes, "operations": operations}


    def crossover(self, parent_1, parent_2):
        """
        crossover between two parents to create 2 new sons.
        parent_1: dictionary, gen data
        parent_2: dictionary, gen data
        return: 2 dictionary, 2 new sons
        """
        # lattery the cross index, one for the modes and another for the operations
        mode_index = random.randint(1, len(parent_1["modes"]) - 2)
        op_index = random.randint(1, len(parent_1["operations"]) - 2)
        # create 2 new sons
        son_1 = self.__crossover(parent_1, parent_2, mode_index, op_index)
        son_2 = self.__crossover(parent_2, parent_1, mode_index, op_index)
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
        if random.random() <= self.op_mutation:
            # lottery an operation on which we will do the motation
            index = random.randint(1, len(son["operations"]) - 1)
            # precede the choisen operation, only if its possible according to the preferences
            for i in range(index):
                if son["operations"][index] in preferences_function(son["operations"][:i]):
                    son["operations"].insert(i, son["operations"].pop(index))

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
        population = self.first_population(job.operations, job.next_operations)
        # calcolate population score by the job fitness function
        fitness = [job.find_ub_ga(genotype["operations"], genotype["modes"])["value"] for genotype in population]
        history.append(sum(fitness) / float(len(fitness)))
        for generation in range(self.generations):
            print(time.time() - start)
            # calcolate the probability of each gen to be selected as parent
            probability = [1 / item for item in fitness]
            F = sum(probability)
            weights = [item / F for item in probability]
            sons = []
            # create |population_size| new sons
            for _ in range(int(self.population_size / 2)):
                parent_1, parent_2 = random.choices(population=population, weights=weights, k=2)
                son_1, son_2 = self.crossover(parent_1, parent_2)
                sons.append(self.mutation(son_1, job.operations, job.next_operations))
                sons.append(self.mutation(son_2, job.operations, job.next_operations))
    
            # add the new sons to the population
            population += sons
            # calcolate sons score
            fitness += [job.find_ub_ga(genotype["operations"], genotype["modes"])["value"] for genotype in population[self.population_size:]]
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
            if fitness[0] == fitness[-1]:
                break

        run_time = time.time() - start
        with open("ga.csv", "a+") as f:
            writer = csv.writer(f)
            writer.writerow(history)

        # return the solution value, number of generations, the taken time and the solution draw data
        solution_draw_data = job.find_ub_ga(population[0]["operations"], population[0]["modes"])["to_draw"]
        # modify the solution title to the GA run time
        solution_draw_data["title"] = "solution in {:.10f} sec\ncreated nodes = 0, max queue size = 0".format(run_time)
        return {"value": fitness[0], "generations": generation, "time": run_time, "feasibles": 0, "to_draw": solution_draw_data, "cross_solutions": 0}