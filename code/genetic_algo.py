import random
import time

class GA:

    def __init__(self, generations = 50, population_size=50, mode_mutation=0.01, op_mutation=0.01):
        self.generations = generations
        self.population_size = population_size
        self.mode_mutation = mode_mutation
        self.op_mutation = op_mutation


    def first_population(self, operations, preferences_function):
        population = []
        for _ in range(self.population_size):
            modes = []
            preferences = []
            for op in operations.values():
                modes.append(random.randint(1, len(op.modes)))

            possible_operations = preferences_function([])
            while possible_operations:
                preferences.append(random.choice(possible_operations))
                possible_operations = preferences_function(preferences)

            population.append({"modes": modes, "operations": preferences})

        return population


    def __crossover(self, parent_1, parent_2, mode_index, op_index):
        modes = parent_1["modes"][0:mode_index] + parent_2["modes"][mode_index:]
        operations = parent_1["operations"][0:op_index]
        for op in parent_2["operations"]:
            if op not in operations:
                operations.append(op)

        return {"modes": modes, "operations": operations}


    def crossover(self, parent_1, parent_2):
        mode_index = random.randint(1, len(parent_1["modes"]) - 2)
        op_index = random.randint(1, len(parent_1["operations"]) - 2)
        son_1 = self.__crossover(parent_1, parent_2, mode_index, op_index)
        son_2 = self.__crossover(parent_2, parent_1, mode_index, op_index)

        return son_1, son_2


    def mutation(self, son, operations, preferences_function):
        if random.random() <= self.mode_mutation:
            op = random.randint(0, len(operations) - 1)
            operation = operations[str(op + 1)]
            mode = random.randint(1, len(operation.modes))
            while len(operation.modes) > 1 and mode == son["modes"][op]:
                mode = random.randint(1, len(operation.modes))

            son["modes"][op] = mode

        if random.random() <= self.op_mutation:
            index = random.randint(1, len(son["operations"]) - 1)
            for i in range(index):
                if son["operations"][index] in preferences_function(son["operations"][:i]):
                    son["operations"].insert(i, son["operations"].pop(index))

        return son


    def solve(self, job):
        start = time.time()
        population = self.first_population(job.operations, job.next_operations)
        fitness = [job.find_UB_ga(genotype["operations"], genotype["modes"])["value"] for genotype in population]
        for generation in range(self.generations):
            # print("generations =", generation)
            probability = [1 / item for item in fitness]
            F = sum(probability)
            weights = [item / F for item in probability]
            sons = []
            for _ in range(int(self.population_size / 2)):
                parent_1, parent_2 = random.choices(population=population, weights=weights, k=2)
                son_1, son_2 = self.crossover(parent_1, parent_2)
                sons.append(self.mutation(son_1, job.operations, job.next_operations))
                sons.append(self.mutation(son_2, job.operations, job.next_operations))
    
            population += sons
            fitness += [job.find_UB_ga(genotype["operations"], genotype["modes"])["value"] for genotype in population[self.population_size:]]
            new_population = []
            new_fitness = []
            for item_from_fitness, item_from_population in sorted(zip(fitness, population), key=lambda pair: pair[0]):
                new_population.append(item_from_population)
                new_fitness.append(item_from_fitness)

            population = new_population[:self.population_size]
            fitness = new_fitness[:self.population_size]

            if fitness[0] == fitness[-1]:
                break

        run_time = time.time() - start
        return {"value": fitness[-1], "generations": generation, "time": run_time}