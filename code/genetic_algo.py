import random

class GA:

    def __init__(self, population_size=50, mode_mutation=0.001, op_mutation=0.001):
        self.population_size = population_size
        self.mode_mutation = mode_mutation
        self.op_mutation = op_mutation


    def first_population(self, operations, preferences_function):
        population = []
        for i in range(self.population_size):
            modes = []
            preferences = []
            for op in operations:
                modes.append(random.randint(1, len(op.modes)))

            possible_operations = preferences_function([])
            while possible_operations:
                preferences.append(random.choice(possible_operations))
                possible_operations = preferences_function(preferences)

            population.append({"modes": modes, "operations": preferences})

        return population


    def crossover(self, parent_1, parent_2):
        mode_index = random.randint(1, len(parent_1["modes"]) - 2)
        op_index = random.randint(1, len(parent_1["operations"]) - 2)
        modes = parent_1["modes"][0:mode_index] + parent_2["modes"][mode_index+1:]
        operations = parent_1["operations"][0:op_index] + parent_2["operations"][op_index+1:]
        son_1 = {"modes": modes, "operations": operations}

        modes = parent_2["modes"][0:mode_index] + parent_1["modes"][mode_index+1:]
        operations = parent_2["operations"][0:op_index] + parent_1["operations"][op_index+1:]
        son_2 = {"modes": modes, "operations": operations}

        return son_1, son_2


    def mutation(self, son):
    

    def solve(operations, fitness_function, preferences_function=next_operations):
        population = self.first_population(operations, preferences_function)
