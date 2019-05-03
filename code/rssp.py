from os import getpid, listdir
import matplotlib.pyplot as plt
import argparse
import time
from sqlite3 import connect
from branch_and_bound import B_and_B
from job import Job

def draw_solution(job_operations, choices, title):
    """
    collecting the data from the cplex solution
    choices: dict, parameters name : value
    title: string, solution time, number of nodes, queue size and max depth
    return: None
    """
    operations = {}
    choices_modes = []
    # for each operation collect which mode were selected, Tim and resources
    for operation_name, op in job_operations:
        mode_found = False
        operations[operation_name] = {}
        operations[operation_name]["resources"] = {}
        resources = None
        for name, val in choices.items():
            # if Xi,m,r,l set to 1 check him
            if name.startswith("X" + operation_name + ",") and val == 1:
                # check if operation's mode already known 
                if not mode_found:
                    # from the mode save it number, needed resources and duration of the mode
                    for mode in op.modes:
                        if name.startswith("X" + operation_name + "," + mode.mode_number):
                            operations[operation_name]["duration"] = mode.tim
                            resources = mode.resources
                            choices_modes.append("operation " + operation_name + "\nmode " + str(mode.mode_number))
                            mode_found = True
                # remove from Xi,m,r,l the X and split the rest by comma
                i, m, r, l = name[1:].split(",")
                # find the appropriate Tr,l for the Xi,m,r,l
                resource_start_time = choices["T" + r + "," + l]
                resource_duration = ""
                # for each resource save it start time and duration
                for resource in resources:
                    if resource.number == r:
                        resource_duration = resource.get_usage_duration(i,m)
                operations[operation_name]["resources"][r] = {"start" : float(resource_start_time), "duration" : resource_duration}
            # save the start time of the operation
            if name == "T" + operation_name:
                operations[operation_name]["start"] = val
    draw_collected_data(operations, title, choices_modes)


def draw_collected_data(operations, title, choices_modes):
    """
    set the axis and draw the collected data
    operations: dict, has all data from cplex
    title: string, solution time, number of nodes, queue size and max depth
    choices_modes: list, for each operation which mode was chosen
    return: None
    """
    start_y = 0
    plt.figure(figsize=(25,10))
    plt.subplots_adjust(left=0.1, right=0.98, bottom=0.1, top=0.9)
    plt.title(title, fontsize=14)
    plt.ylabel('operation & modes', fontsize=16)
    plt.xlabel('time', fontsize=16)
    x_ticks = []
    for op in operations.values():
        div = len(op["resources"])
        x_ticks.append(op["start"])
        x_ticks.append(op["start"] + op["duration"])
        drow_rectangle(start_y, start_y + 1, op)
        index = 0
        for resource_name, resource in op["resources"].items():
            drow_rectangle(start_y + index / div, start_y + (index + 1) / div, resource, 1, "r" + resource_name)
            index += 1
        start_y += 1
    plt.xticks(list(set(x_ticks)))
    plt.yticks([0.5 + i for i in range(len(operations) + 1)], choices_modes)
    for i in range(len(operations) + 1):
        plt.axhline(i, color='black')
    plt.show()


def drow_rectangle(start_y, end_y, value, width=2, text=""):
    """
    draw rectangle.
    start_y: float, from where the rectangle start
    end_y: float, where the rectangle end
    value: dict, data for the x axis
    width: float, the width of the rectangle
    text: string, what to write in the rectangle
    return: None
    """
    if text:
        linestyle = "-"
    else:
        linestyle = ":"
    y = [start_y + 0.01, start_y + 0.01, end_y - 0.01, end_y - 0.01, start_y + 0.01]
    x = [value["start"], value["start"] + value["duration"],
            value["start"] + value["duration"], value["start"], value["start"]]
    plt.plot(x,y, linestyle=linestyle, linewidth=width)
    plt.text(value["start"] + 0.1, start_y + 0.03, text, fontsize=8)


def check_problem_number(problem_number):
    """
    check if the wanted problem exist and if not raise argparse exception.
    return: number, the problem number if its exist
    """
    conn = connect('data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM OpMoRe where Problem_ID = {0}".format(problem_number))
    query = c.fetchall()
    conn.close()
    if not query:
        msg = "Problem number %r not exist" % problem_number
        raise argparse.ArgumentTypeError(msg)
    return problem_number


def arguments_parser():
    usage = 'usage...'
    parser = argparse.ArgumentParser(description=usage, prog='rssp.py')
    parser.add_argument('-p', '--problem_number', type=check_problem_number, required=True,
        help='the wanted problem number to be solved')
    parser.add_argument('-c', '--cplex_auto_solution', action='store_true',
        help='use cplex librarys for full MILP solution')
    parser.add_argument('-l', '--init_resource_by_labels', action='store_true',
        help='try initialze every resources lables one by one')
    parser.add_argument('--sp', action='store_true',
        help='divide the problem to SP\'s')
    parser.add_argument('-s', '--sort_x_by', choices=['pre', 'res'],
        help='sort the Xi,m,r,l according to the chooses sort')
    parser.add_argument('-r', '--resource_sort_type', choices=['bigger', 'lower'],
        help='sort the Xi,m,r,l by resources according to the chooses sort {bigger/lower}')
    args = parser.parse_args()
    if args.sort_x_by == "res" and not args.resource_sort_type:
        msg = "when chooses sort x by resources, must be chooses the sort type {bigger/lower}"
        raise parser.error(msg)
    return args


def main():
    print("pid =", getpid())
    args = arguments_parser()
    job = Job(args.problem_number, args.cplex_auto_solution, args.sort_x_by, args.resource_sort_type == "lower")
    print("|Xi,m,r,l| =", len(job.x_names), "\n|equations| =", len(job.cplex["rownames"]), "\nPrediction UB =", job.UB)
    print("starting solve")
    start = time.time()
    BB = B_and_B(job.cplex["obj"], job.cplex["ub"], job.cplex["lb"], job.cplex["ctype"],
                job.cplex["colnames"], job.cplex["rhs"], job.cplex["rownames"],
                job.cplex["sense"], job.cplex["rows"], job.cplex["cols"], job.cplex["vals"],
                job.x_names, job.UB, args.sp)
    choices, solution_data = BB.solve_algorithem(args.init_resource_by_labels, disable_prints=False)
    end = time.time()
    solution_data = "solution in %10f sec\n" % (end - start) + str(solution_data)
    if choices and solution_data:
        draw_solution(job.operations.items(), choices, solution_data)


if __name__ == '__main__':
    main()