from resource import Resource
from operation import Operation
import sys
import csv

class Job:

    def __init__(self, csv_path):
        self.path = csv_path
        self.N = sys.maxsize
        self.resources = {}
        self.operations = {}
        self.preferences = {}

    def initialize(self):
        with open(self.path, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader[1:]:
                print(row)
                if row["resource"] not in self.resources:
                    self.resources[row["resource"]] = Resource(row["resource"])
                if row["operation"] not in self.operations:
                    self.operations[row["operation"]] = Operation(row["operation"])
                self.operations[row["operation"]].add_mode_to_operation(row["mode"], self.resources[row["resource"]], row["start"], row["duration"])
                self.preferences[row["preferences"]] = row["preferences"].split(";")


    def __str__(self):
        return str(self.operations)

gob1 = Job("data.csv")
print(gob1)
