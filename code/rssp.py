from sqlite3 import OperationalError
from os import getpid, listdir, stat
import matplotlib.pyplot as plt
import argparse
import time
from sqlite3 import connect
from branch_and_bound import B_and_B
from job import Job
from subprocess import Popen, PIPE
import sys

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
        operations[operation_name] = {"resources": {}}
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
                resource_duration = None
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
        draw_rectangle(start_y, start_y + 1, op)
        index = 0
        for resource_name, resource in op["resources"].items():
            draw_rectangle(start_y + index / div, start_y + (index + 1) / div, resource, 1, "r" + resource_name)
            index += 1

        start_y += 1

    plt.xticks(list(set(x_ticks)))
    plt.yticks([0.5 + i for i in range(len(operations) + 1)], choices_modes)
    for i in range(len(operations) + 1):
        plt.axhline(i, color='black')

    plt.show()


def draw_rectangle(start_y, end_y, value, width=2, text=""):
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
    x = [value["start"], value["start"] + value["duration"], value["start"] + value["duration"], value["start"], value["start"]]
    plt.plot(x, y, linestyle=linestyle, linewidth=width)
    plt.text(value["start"] + 0.1, start_y + 0.03, text, fontsize=8)


def save_solutions(name, problem_id, solution):
    conn = connect('data.db')
    c = conn.cursor()
    c.execute(f"SELECT Solution FROM BestSolution where Problem_ID = {problem_id} AND Solution_type = '{name}'")
    query = c.fetchall()
    if not query or query[0][0] > solution['value']:
        if query:
            c.execute(f"DELETE FROM BestSolution WHERE Problem_ID = {problem_id} AND Solution_type = '{name}'")
            c.execute(f"DELETE FROM Solution WHERE Problem_ID = {problem_id} AND Solution_type = '{name}'")
            conn.commit()

        add_best_solution = f"insert into BestSolution values ('{name}', {problem_id}, {solution['value']}, " \
                            f"{round(solution['time'], 2)}, {solution['cross_resources']}, {solution['feasibles']}, " \
                            f"{solution['improved_generation']}, {solution['origin'].get('greedy', 0)}, " \
                            f"{solution['origin'].get('ga', 0)})"
        c.execute(add_best_solution)

        for (op_name, op_values), mode in zip(solution['to_draw']['operations'].items(), solution['to_draw']['choices_modes']):
            mode = mode.split("\n")[1][4:]  # mode = 'operation #\nmode #' -> split to remove the operaation part, [4,:] to remove the 'mode'
            add_solution = f"insert into Solution values ('{name}', {problem_id}, {op_name}, " \
                           f"{mode}, {op_values['start']})"
            c.execute(add_solution)

        conn.commit()

    conn.close()


def solve_problem(args):
    job = Job(args.problem_number, cplex_solution=args.solution_type, ub=args.ub, sort_x=args.sort_x, reverse=args.sort_x and args.reverse, repeat=args.repeate, create_csv=args.output_to_csv,
              timeout=args.timeout, mutation_chance=args.mutation_chance, changed_mutation=args.changed_mutation, ageing=args.ageing, complex_ageing=args.complex_ageing)
    print("|Xi,m,r,l| =", len(job.x_names), "\n|equations| =", len(job.cplex["rownames"]), "\nPrediction UB =", job.UB, "\nLB =", job.LB, "\nLB_res =", job.LB_res)
    start = time.time()
    if job.UB == job.LB_res or args.solution_type == "None":
        print("LB = UB")
        if args.graph_solution:
            draw_collected_data(job.draw_UB["operations"], job.draw_UB["title"], job.draw_UB["choices_modes"])

        choices, nodes, queue_size, SPs_value, solution_value, MIP_infeasible = None, 0, 0, 0, job.UB, "False"
    else:
        print("starting solve B&B")
        BB = B_and_B(job.cplex["obj"], job.cplex["ub"], job.cplex["lb"], job.cplex["ctype"],
                     job.cplex["colnames"], job.cplex["rhs"], job.cplex["rownames"],
                     job.cplex["sense"], job.cplex["rows"], job.cplex["cols"], job.cplex["vals"],
                     job.x_names, job.LB_res, job.UB, args.sp)

        choices, nodes, queue_size, SPs_value, solution_value, MIP_infeasible = BB.solve_algorithem(args.init_resource_by_labels,
                                                                                                    disable_prints=False,
                                                                                                    cplex_auto_solution=args.solution_type == "cplex")
    end = time.time()
    solution_data = "solution in {:.10f} sec\ncreated nodes = {}, max queue size = {}".format(end - start, nodes, queue_size)
    if args.graph_solution and choices and solution_data:
        draw_solution(job.operations.items(), choices, solution_data)

    solution = "{}, {}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {}, {:.3f}, {}, {}, {}, {}, {}".format(len(job.operations), len(job.resources), job.get_mean_modes(), job.get_mean_r_im(), job.count_pref, job.avg_t_im(), job.avg_h_im(), job.avg_d_im(),
                                                                                                                                                       job.get_r_im_range(range_mean=True), job.get_r_im_range(range_stdev=True), job.get_r_im_range(range_median=True), job.get_r_im_range(
            range_cv=True),
                                                                                                                                                       job.get_r_im_range(range_range=True), job.cross_resources, end - start, nodes, queue_size, MIP_infeasible, job.longest_preferences_path,
                                                                                                                                                       job.mean_preferences_path)
    bounds_greedy_and_ga_data = "{}, {}, {}".format(job.LB, job.LB_res, job.UB)
    if job.greedy_all:
        bounds_greedy_and_ga_data += ", {}".format(job.greedy_all)
    for ub_name, ub_solution in job.UBs.items():
        while True:
            try:
                save_solutions(ub_name, args.problem_number, ub_solution)
                break
            except OperationalError as e:
                print(e)

        if args.ub in ["ga_one_line_cross_final_solution", "ga_one_line_cross_best_solution"]:
            bounds_greedy_and_ga_data += ", {}, {}, {:.3f}, {:.3f}, {:.3f}, {}, {}, {}".format(ub_solution["value"], ub_solution["cross_value"], ub_solution["time"], ub_solution["cross_time"], ub_solution["feasibles"], ub_solution["cross_resources"], ub_solution["improved_generation"] ,ub_solution["cross_best_solution"])
        else:
            solution_origin = str(ub_solution["origin"])
            solution_origin = solution_origin.replace(" ", "").replace("{", "").replace("}", "").replace("'", "").replace(":", "=").replace(",", ";")
            bounds_greedy_and_ga_data += ", {}, {:.3f}, {:.3f}, {}, {}, {}, {}".format(ub_solution["value"], ub_solution["time"], ub_solution["feasibles"], ub_solution["cross_resources"], ub_solution["improved_generation"], solution_origin ,ub_solution["cross_best_solution"])

    return solution, SPs_value, bounds_greedy_and_ga_data, solution_value


def check_problem_number(problem_number):
    """
    check if the wanted problem exist and if not raise argparse exception.
    return: number, the problem number if its exist
    """
    problem_number = problem_number.replace(" ", "")
    problems = problem_number.split(",")
    while True:
        try:
            conn = connect('data.db')
            c = conn.cursor()
            for index, problem in enumerate(problems):
                problem = problem.split("-")
                problems[index] = problem
                c.execute("SELECT * FROM OpMoRe where Problem_ID = {0}".format(problem[-1]))
                query = c.fetchall()
                if not query:
                    msg = "Problem number %r not exist" % problem
                    raise argparse.ArgumentTypeError(msg)

            conn.close()
            break
        except OperationalError as e:
            print(e)

    return problems


def arguments_parser():
    usage = 'usage...'
    parser = argparse.ArgumentParser(description=usage, prog='rssp.py')
    parser.add_argument('--ub', choices=['ga1_res', "ga1_op", 'ga2s', 'ga2m', 'ga2s_all', 'ga2s_final', 'ga2s_select_1', 'ga2s_select_quarter', 'ga2s_select_all', 'ga2s_ga2s_all', 'greedy', 'greedy_ga2s_all', 'greedy_ga2s_ga2s_all', 'none'],
        help='run 4 GA or/and 4 different greedy algorithm to calculate problems UB')
    parser.add_argument('-p', '--problem_number', type=check_problem_number, required=True,
        help='the wanted problems number to be solved. for range of problems use "-". to solve multi ranges seperate them by ",". exsample: "1-10, 15, 16, 18-21"')
    parser.add_argument('-s', '--solution_type', choices=['cplex', 'b&b', 'None'],
        help='use cplex librarys for full MILP solution')
    parser.add_argument('-l', '--init_resource_by_labels', action='store_true',
        help='try initialze every resources lables one by one')
    parser.add_argument('--sp', action='store_true',
        help='divide the problem to SP\'s')
    parser.add_argument('-g', "--graph_solution", action='store_true',
        help='disable the show of the solution with graphs')
    parser.add_argument('-a', "--all_flags", action='store_true',
        help='for every selected problem run all 16 options')
    parser.add_argument('-r', "--repeate", type=int, default=1,
        help='duplicate the problem to increace its size')
    parser.add_argument('-o', "--output_to_csv", action='store_true',
        help='for every selected problem run all 16 options')
    parser.add_argument('-t', "--timeout", type=int,
        help='for every selected problem run all 16 options')
    parser.add_argument('-m', "--mutation_chance", type=float, default=0.04,
        help='for every selected problem run all 16 options')
    parser.add_argument('-c', "--changed_mutation", action='store_true',
        help='for every selected problem run all 16 options')
    parser.add_argument("--ageing", action='store_true',
        help='for every selected problem run all 16 options')
    parser.add_argument("--complex_ageing", action='store_true',
        help='for every selected problem run all 16 options')
    parser.add_argument("--parallel", type=int,
        help='for every selected problem run all 16 options')
    parser.add_argument("--ignore", type=int,
        help='for every selected problem run all 16 options')
    parser.add_argument("--use_greedy", action='store_true',
        help='for every selected problem run all 16 options')
    subparsers = parser.add_subparsers(dest='sort_x',
        help='sort xi,m,r,l')
    preferences_parser = subparsers.add_parser('pre',
        help='sort Xi,m,r,l by operation preferences')
    preferences_parser.add_argument('-r', '--reverse', action='store_true',
        help='use reverse sort of the preferences')
    resources_parser = subparsers.add_parser('res',
        help='sort Xi,m,r,l by resources')
    resources_parser.add_argument('-r', '--reverse', action='store_true',
        help='use reverse sort of the resources')
    return parser.parse_args()


def run_main(args, f, problem):
    print("problem number:", problem)
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    print("local time:", current_time)
    SPs_value = 0
    bounds_greedy_and_ga_data = ""
    args.problem_number = problem
    # try:
    if args.all_flags:
        layouts = [{"init_resource_by_labels" : False, "sp" : False},
                {"init_resource_by_labels" : True, "sp" : False},
                {"init_resource_by_labels" : False, "sp" : True},
                {"init_resource_by_labels" : True, "sp" : True}]
        sort_bys = [{"sort_x" : None, "reverse" : False},
                {"sort_x" : "pre", "reverse" : False},
                {"sort_x" : "res", "reverse" : False},
                {"sort_x" : "res", "reverse" : True}]
        for layout in layouts:
            for sort_by in sort_bys:
                args.init_resource_by_labels = layout["init_resource_by_labels"]
                args.sp = layout["sp"]
                args.sort_x = sort_by["sort_x"]
                args.reverse = sort_by["reverse"]
                solution, SPs_value, bounds_greedy_and_ga_data, solution_value = solve_problem(args)
                f.write(solution + ", ")

        f.write("{},{},{}\n".format(SPs_value, bounds_greedy_and_ga_data, solution_value))

    else:
        solution, SPs_value, bounds_greedy_and_ga_data, solution_value = solve_problem(args)
        f.write("{}, {}, {}, {}\n".format(problem, solution, bounds_greedy_and_ga_data, solution_value))


def main():
    print("pid =", getpid())
    args = arguments_parser()
    args.greedys = ["operations", "loaded_shortest_modes", "modes", "precedence_forward", "precedence_backwards", "precedence_sons", "precedence_all", "precedence_time_forward", "greedy_sum_precedences", "greedy_by_best_precedences"]
    f = open("solutions.txt", "a")
    if stat("solutions.txt").st_size == 0:
        f.write("Problem_ID, |Operations|, |Resources|, Avg(Mi), Avg(Rim), Avg(pref), Avg(Tim), Avg(Him), Avg(Dim), Rim_mean, Rim_stdev, Rim_median, Rim_CV, Rim_range, Cross_resources, Total_run_time, Nodes, Queue_size, MIP_infeasible, longest_preceding, mean_preceding, LB, LB_res, UB")
        titles = []
        if args.ub:
            if args.ub == "greedy" or args.ub.startswith("greedy"):
                titles += args.greedys
                f.write(", greedy_all")
                #titles += ["greedy_{}".format(i) for i in range(1,8)]

            if args.ub.startswith("ga") or "ga" in args.ub:
                titles += ["GA_{}".format(i) for i in range(1,11)]

        for t in titles:
            if args.ub in ["ga2s_final", "ga2s_select_1"]:
                f.write(", {title}, cross_{title}, time, cross_time, feasibles, cross_resources, improved_generation, cross_best_solution".format(title=t))
            else:
                f.write(", {title}, time, feasibles, cross_resources, improved_generation, origin, cross_best_solution".format(title=t))

        f.write(", solution\n")
        f.close()

    f = open("solutions.txt", "a")
    problems_list = args.problem_number[:]
    parallel_jobs = []
    for problems in problems_list:
        problems += ["{}".format(int(problems[0]))]
        start = int(problems[0])
        end = int(problems[1]) + 1
        for problem in range(start, end):
            if args.parallel:
                while len(parallel_jobs) == args.parallel:
                    for p in parallel_jobs:
                        if p.poll() is not None:
                            parallel_jobs.remove(p)

                child_args = ["python"] + sys.argv[:]
                try:
                    problem_number_index = child_args.index("-p") + 1
                except NameError:
                    problem_number_index = child_args.index("--problem_number") + 1

                child_args[problem_number_index] = str(problem)
                child_args[child_args.index("--parallel")] = "--ignore"
                parallel_jobs.append(Popen(child_args))

            else:
                run_main(args, f, problem)

    for p in parallel_jobs:
        p.wait()

    f.close()

if __name__ == '__main__':
    main()
