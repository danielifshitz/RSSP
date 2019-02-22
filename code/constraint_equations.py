def get_next_row_index(cplex_d):
    """
    create new row, add it to all rows and return its index
    cplex_d: dict, all cplex data
    return: int, next row index
    """
    row_index = len(cplex_d["rownames"])
    row_name = "r" + str(row_index)
    cplex_d["rownames"].append(row_name)
    return row_index


def add_row_col_val(cplex_d, col, row_index, val):
    """
    add parameter data.
    cplex_d: dict, all cplex data
    col: string, parameter name
    row_index: int, row index
    val: float, coefficient value 
    return: None
    """
    col_index = cplex_d["colnames"].index(col)
    cplex_d["cols"].append(col_index)
    cplex_d["rows"].append(row_index)
    cplex_d["vals"].append(val)


def add_rows_cols_vals(cplex_d, cols_list, rows_list, vals_list):
    """
    add parameters data.
    cplex_d: dict, all cplex data
    cols_list: list, cols index
    rows_list: list, rows index
    vals_list: list, vals index 
    return: None
    """
    cplex_d["cols"] += cols_list
    cplex_d["rows"] += rows_list
    cplex_d["vals"] += vals_list


def first_equations(operations, cplex_d):
    for operation in operations.values():
        row_index = get_next_row_index(cplex_d)
        for mode in operation.modes:
            for index in range(1, mode.r_tag.size + 1):
                x_i_m_r_l = "X{},{},{},{}".format(operation.number, mode.mode_number, mode.r_tag.number, index)
                add_row_col_val(cplex_d, x_i_m_r_l, row_index, 1)
        cplex_d["sense"] += "E"
        cplex_d["rhs"].append(1)


def second_equations(operations, cplex_d):
    for operation in operations.values():
        for mode in operation.modes:
            r_tag_cols = []
            r_tag_rows = []
            r_tag_vals = []
            for index in range(1, mode.r_tag.size + 1):
                x_i_m_r_l = "X{},{},{},{}".format(operation.number, mode.mode_number, mode.r_tag.number, index)
                col_index = cplex_d["colnames"].index(x_i_m_r_l)
                r_tag_cols.append(col_index)
                r_tag_vals.append(1)
            for resource in mode.resources:
                if resource.number != mode.r_tag.number:
                    row_index = get_next_row_index(cplex_d)
                    r_tag_rows = [row_index] * len(r_tag_cols)
                    add_rows_cols_vals(cplex_d, r_tag_cols, r_tag_rows, r_tag_vals)
                    for index in range(1, resource.size + 1):
                        x_i_m_r_l = "X{},{},{},{}".format(operation.number, mode.mode_number, resource.number, index)
                        add_row_col_val(cplex_d, x_i_m_r_l, row_index, -1)
                    cplex_d["sense"] += "E"
                    cplex_d["rhs"].append(0)


def third_equations(resources, cplex_d):
    for resource in resources.values():
        pre_cols = []
        pre_rows = []
        pre_vals = []
        row_index = get_next_row_index(cplex_d)
        for op_mode in resource.usage.keys():
            x_i_m_r_l = "X{},{},1".format(op_mode, resource.number)
            add_row_col_val(cplex_d, x_i_m_r_l, row_index, 1)
            pre_cols.append(cplex_d["colnames"].index(x_i_m_r_l))
            pre_vals.append(1)
        cplex_d["sense"] += "L"
        cplex_d["rhs"].append(1)
        pre_vals = [x * -1 for x in pre_vals]
        for index in range(2, resource.size + 1):
            next_cols = []
            next_vals = []
            row_index = get_next_row_index(cplex_d)
            for op_mode in resource.usage.keys():
                x_i_m_r_l = "X{},{},{}".format(op_mode, resource.number, index)
                add_row_col_val(cplex_d, x_i_m_r_l, row_index, 1)
                next_cols.append(cplex_d["colnames"].index(x_i_m_r_l))
                next_vals.append(1)
            pre_rows = [row_index] * len(pre_cols)
            add_rows_cols_vals(cplex_d, pre_cols, pre_rows, pre_vals)
            pre_vals = [x * -1 for x in next_vals]
            pre_cols = next_cols
            cplex_d["sense"] += "L"
            cplex_d["rhs"].append(0)


def fourth_equations(operations, preferences, cplex_d):
    for op_number, preferences in preferences.items():
        if preferences != None: # check if the operation have preferences
            for preference_op in preferences:
                row_index = get_next_row_index(cplex_d)
                t_i = "T" + str(preference_op.number)
                add_row_col_val(cplex_d, t_i, row_index, 1)
                for mode in preference_op.modes:
                    for index in range(1, mode.r_tag.size + 1):
                        x_i_m_r_l = "X{},{},{},{}".format(preference_op.number, mode.mode_number, mode.r_tag.number, index)
                        add_row_col_val(cplex_d, x_i_m_r_l, row_index, mode.tim)
                t_i = "T" + str(op_number)
                add_row_col_val(cplex_d, t_i, row_index, -1)
                cplex_d["sense"] += "L"
                cplex_d["rhs"].append(0)


def fifth_equations(resources, cplex_d):
    for resource in resources.values():
        for index in range (2, resource.size + 1):
            row_index = get_next_row_index(cplex_d)
            t_r_l_prev = "T{},{}".format(resource.number,index - 1)
            add_row_col_val(cplex_d, t_r_l_prev, row_index, 1)
            for op_mode, usage in resource.usage.items():
                x_i_m_r_l = "X{},{},{}".format(op_mode, resource.number, index - 1)
                add_row_col_val(cplex_d, x_i_m_r_l, row_index, usage["duration"])
            t_r_l = "T{},{}".format(resource.number,index)
            add_row_col_val(cplex_d, t_r_l, row_index, - 1)
            cplex_d["sense"] += "L"
            cplex_d["rhs"].append(0)


def sixth_equations(operations, N, cplex_d):
    for operation in operations.values():
        for resource, modes in operation.all_resources.items():
            for index in range(1, resource.size + 1):
                cols_list = []
                vals_list = []
                x_i_m_r_l_list = []
                t_i = "T{}".format(operation.number)
                cols_list.append(cplex_d["colnames"].index(t_i))
                vals_list.append(1)
                t_r_l = "T{},{}".format(resource.number, index)
                cols_list.append(cplex_d["colnames"].index(t_r_l))
                vals_list.append(-1)
                for mode in modes:
                    op_mode = operation.number + ',' + mode
                    t_start = resource.usage[op_mode]["start_time"]
                    x_i_m_r_l = "X{},{},{},{}".format(operation.number, mode, resource.number, index)
                    cols_list.append(cplex_d["colnames"].index(x_i_m_r_l))
                    vals_list.append(t_start)
                    x_i_m_r_l_list.append(len(cols_list) - 1)
                for x_i_m_r_l in x_i_m_r_l_list:
                    vals_list[x_i_m_r_l] -= N
                row_list = [get_next_row_index(cplex_d)] * len(cols_list)
                add_rows_cols_vals(cplex_d, cols_list, row_list, vals_list)
                cplex_d["sense"] += "G"
                cplex_d["rhs"].append(-N)
                for x_i_m_r_l in x_i_m_r_l_list:
                    vals_list[x_i_m_r_l] += 2*N
                row_list = [get_next_row_index(cplex_d)] * len(cols_list)
                add_rows_cols_vals(cplex_d, cols_list, row_list, vals_list)
                cplex_d["sense"] += "L"
                cplex_d["rhs"].append(N)


def seventh_equations(operations, cplex_d):
    for operation in operations.values():
        row_index = get_next_row_index(cplex_d)
        t_i = "T" + str(operation.number)
        add_row_col_val(cplex_d, t_i, row_index, 1)
        for mode in operation.modes:
            for index in range(1, mode.r_tag.size + 1):
                x_i_m_r_l = "X{},{},{},{}".format(operation.number, mode.mode_number, mode.r_tag.number, index)
                add_row_col_val(cplex_d, x_i_m_r_l, row_index, mode.tim)
        add_row_col_val(cplex_d, "F", row_index, -1)
        cplex_d["sense"] += "L"
        cplex_d["rhs"].append(0)


def eighth_equations(resources, cplex_d):
    for resource in resources.values():
        for index in range (1, resource.size + 1):
            row_index = get_next_row_index(cplex_d)
            t_r_l = "T{},{}".format(resource.number,index)
            add_row_col_val(cplex_d, t_r_l, row_index, 1)
            for op_mode, usage in resource.usage.items():
                x_i_m_r_l = "X{},{},{}".format(op_mode, resource.number, index)
                add_row_col_val(cplex_d, x_i_m_r_l, row_index, usage["duration"])
            add_row_col_val(cplex_d, "F", row_index, -1)
            cplex_d["sense"] += "L"
            cplex_d["rhs"].append(0)
