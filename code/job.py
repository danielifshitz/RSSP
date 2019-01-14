from job_operation import Operation
from job_resource import Resource
import sys
import csv

class Job:

    def __init__(self, csv_path):
        self.path = csv_path
        self.N = sys.maxsize
        self.resources = {}
        self.operations = {}
        self.preferences = {}
        self.__initialize()
        self.__find_rtag_tim()

    def __initialize(self):
        with open(self.path, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                if row["resource"] not in self.resources:
                    self.resources[row["resource"]] = Resource(row["resource"])
                if row["operation"] not in self.operations:
                    self.operations[row["operation"]] = Operation(row["operation"])
                self.operations[row["operation"]].add_mode_to_operation(row["mode"], self.resources[row["resource"]], row["start"], row["duration"])
                self.preferences[row["preferences"]] = row["preferences"].split(";")

    def __find_rtag_tim(self):
        for op in self.operations:
            for mode in op.modes:
                mode.find_rtag()
                mode.find_tim()

    def __str__(self):
        string = ""
        for key, value in self.operations.items():
            string += str(key) + " : { " + str(value) + " \n}\n"
        return string

ob1 = Job("data.csv")
print(gob1)
