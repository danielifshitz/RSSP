class Equations:
    def __init__(self, equations, is_integer=False):
        self.value = -1 # the value of the variables
        self.solution = 0
        self.is_integer = False
        self.__calc(equations, is_integer)


    def __calc(self, equations, is_integer):
        self.solution = equations
        self.value = 0
        self.is_integer = is_integer


    def get_solution(self):
        return self.solution


    def is_integer_sulotion(self):
        return self.is_integer


    def __str__(self):
        return str(self.get_solution())