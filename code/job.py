from resource import Resource
from operation import Operation
import sys.maxint as maxInt
import csv

class Job:

    def __init__(self, csv_path):
        self.path = csv_path
        self.N = maxInt
        self.resources = []
        self.resources_num = []
        self.operations = []
        self.operations_num = []

    def initialize(self):
        with open(self.path, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader[1:]:
                if row["resource"] not in self.resources_num:
                    self.resources.append(Resource(row["resource"]))
                    self.resources_num.append(row["resource"])
                if row["operation"] not in self.operations_num:
                    self.operations.append(Operation(row["operation"]))
                    self.operations_num.append(row["operation"])



