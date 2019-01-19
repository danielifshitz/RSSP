def first_equations(operations):
    string = ""
    for operation in operations.values():
        for mode in operation.modes:
            for index in range(1, mode.r_tag.size + 1):
                string += " + X{},{},{},{}".format(operation.num_of_op, mode.num_mode, mode.r_tag.number, index)
        string += " = 1\n"
    print(string)

def second_equations(operations):
    string = ""
    for operation in operations.values():
        for mode in operation.modes:
            r_tag_equation = ""
            for index in range(1, mode.r_tag.size + 1):
                r_tag_equation += " + X{},{},{},{}".format(operation.num_of_op, mode.num_mode, mode.r_tag.number, index)
            for resource in mode.needed_resources:
                if resource.number != mode.r_tag.number:
                    r_equation = ""
                    for index in range(1, resource.size + 1):
                        r_equation += " - X{},{},{},{}".format(operation.num_of_op, mode.num_mode, mode.r_tag.number, index)
                    string += r_tag_equation + r_equation + " = 0\n"
    print(string)

def third_equations(resources):
    string = ""
    for resource in resources.values():
        first_eq = ""
        for op_mode in resource.usage.keys():
            first_eq += " + X{},{},1".format(op_mode, resource.number)
        string += first_eq + " <= 1\n"
        for index in range(2, resource.size + 1):
            string += first_eq
            for op_mode in resource.usage.keys():
                string += " - X{},{},{}".format(op_mode, resource.number, index)
            string += first_eq + " <= 0\n"
    print(string)

def Fourth_equations(operations, preferences):
    string = ""
    for op_num, preferences in preferences.items():
        if preferences != None: # check if the operation have preferences
            for preference_op in preferences:
                string += " + T" + str(preference_op.num_of_op)
                for mode in preference_op.modes:
                    for index in range(1, mode.r_tag.size + 1):
                        string += " + {} * X{},{},{},{}".format(mode.tim, preference_op.num_of_op, mode.num_mode, mode.r_tag.number, index)
                op = [op for op in operations.values() if op.num_of_op == op_num]
                string += " - T" + str(op[0].num_of_op) + " <= 0\n"
    print(string)