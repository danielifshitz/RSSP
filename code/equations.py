def get_next_row_index(cplex_d):
    row_index = len(cplex_d["rownames"])
    row_name = "r" + str(row_index)
    cplex_d["rownames"].append(row_name)
    return row_index

def add_row_col_val(cplex_d, col, row_index, val):
    col_index = cplex_d["colnames"].index(col)
    cplex_d["cols"].append(col_index)
    cplex_d["rows"].append(row_index)
    cplex_d["vals"].append(val)

def add_rows_cols_vals(cplex_d, cols_list, rows_list, vals_list):
    cplex_d["cols"] += cols_list
    cplex_d["rows"] += rows_list
    cplex_d["vals"] += vals_list

def first_equations(operations, cplex_d):
    # string = ""
    for operation in operations.values():
        row_index = get_next_row_index(cplex_d)
        for mode in operation.modes:
            for index in range(1, mode.r_tag.size + 1):
                x_i_m_r_l = "X{},{},{},{}".format(operation.num_of_op, mode.num_mode, mode.r_tag.number, index)
                add_row_col_val(cplex_d, x_i_m_r_l, row_index, 1)
                # string += " + X{},{},{},{}".format(operation.num_of_op, mode.num_mode, mode.r_tag.number, index)
        cplex_d["sense"] += "E"
        cplex_d["rhs"].append(1)
        # string += " = 1\n"
    # print(string)
    # print(cplex_d)

def second_equations(operations, cplex_d):
    # string = ""
    for operation in operations.values():
        for mode in operation.modes:
            # r_tag_equation = ""
            r_tag_cols = []
            r_tag_rows = []
            r_tag_vals = []
            for index in range(1, mode.r_tag.size + 1):
                x_i_m_r_l = "X{},{},{},{}".format(operation.num_of_op, mode.num_mode, mode.r_tag.number, index)
                col_index = cplex_d["colnames"].index(x_i_m_r_l)
                r_tag_cols.append(col_index)
                r_tag_vals.append(1)
                # r_tag_equation += " + X{},{},{},{}".format(operation.num_of_op, mode.num_mode, mode.r_tag.number, index)
            for resource in mode.needed_resources:
                if resource.number != mode.r_tag.number:
                    row_index = get_next_row_index(cplex_d)
                    r_tag_rows = [row_index] * len(r_tag_cols)
                    add_rows_cols_vals(cplex_d, r_tag_cols, r_tag_rows, r_tag_vals)
                    # r_equation = ""
                    for index in range(1, resource.size + 1):
                        x_i_m_r_l = "X{},{},{},{}".format(operation.num_of_op, mode.num_mode, resource.number, index)
                        add_row_col_val(cplex_d, x_i_m_r_l, row_index, -1)
                        # r_equation += " - X{},{},{},{}".format(operation.num_of_op, mode.num_mode, resource.number, index)
                    # string += r_tag_equation + r_equation + " = 0\n"
                    cplex_d["sense"] += "E"
                    cplex_d["rhs"].append(0)
    # print(string)
    # print(cplex_d)

def third_equations(resources, cplex_d):
    # string = ""
    for resource in resources.values():
        # pre_eq = ""
        pre_cols = []
        pre_rows = []
        pre_vals = []
        row_index = get_next_row_index(cplex_d)
        for op_mode in resource.usage.keys():
            x_i_m_r_l = "X{},{},1".format(op_mode, resource.number)
            add_row_col_val(cplex_d, x_i_m_r_l, row_index, 1)
            pre_cols.append(cplex_d["colnames"].index(x_i_m_r_l))
            pre_vals.append(1)
            # pre_eq += " + X{},{},1".format(op_mode, resource.number)
        cplex_d["sense"] += "L"
        cplex_d["rhs"].append(1)
        pre_vals = [x * -1 for x in pre_vals]
        # string += pre_eq + " <= 1\n"
        # pre_eq = pre_eq.replace("+", "-")
        for index in range(2, resource.size + 1):
            next_cols = []
            next_vals = []
            row_index = get_next_row_index(cplex_d)
            # next_eq = ""
            for op_mode in resource.usage.keys():
                x_i_m_r_l = "X{},{},{}".format(op_mode, resource.number, index)
                add_row_col_val(cplex_d, x_i_m_r_l, row_index, 1)
                next_cols.append(cplex_d["colnames"].index(x_i_m_r_l))
                next_vals.append(1)
                # next_eq += " + X{},{},{}".format(op_mode, resource.number, index)
            pre_rows = [row_index] * len(pre_cols)
            add_rows_cols_vals(cplex_d, pre_cols, pre_rows, pre_vals)
            pre_vals = [x * -1 for x in next_vals]
            pre_cols = next_cols
            cplex_d["sense"] += "L"
            cplex_d["rhs"].append(0)
            # string +=  next_eq + pre_eq + " <= 0\n"
            # pre_eq = next_eq.replace("+", "-")
    # print(string)
    # print(cplex_d)

def Fourth_equations(operations, preferences, cplex_d):
    # string = ""
    for op_num, preferences in preferences.items():
        if preferences != None: # check if the operation have preferences
            for preference_op in preferences:
                row_index = get_next_row_index(cplex_d)
                t_i = "T" + str(preference_op.num_of_op)
                add_row_col_val(cplex_d, t_i, row_index, 1)
                # string += " + T" + str(preference_op.num_of_op)
                for mode in preference_op.modes:
                    for index in range(1, mode.r_tag.size + 1):
                        x_i_m_r_l = "X{},{},{},{}".format(preference_op.num_of_op, mode.num_mode, mode.r_tag.number, index)
                        add_row_col_val(cplex_d, x_i_m_r_l, row_index, mode.tim)
                        # string += " + {} * X{},{},{},{}".format(mode.tim, preference_op.num_of_op, mode.num_mode, mode.r_tag.number, index)
                t_i = "T" + str(op_num)
                add_row_col_val(cplex_d, t_i, row_index, -1)
                cplex_d["sense"] += "L"
                cplex_d["rhs"].append(0)
                # string += " - T" + str(op_num) + " <= 0\n"
    # print(string)
    # print(cplex_d)