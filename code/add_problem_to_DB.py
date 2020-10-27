import csv
import argparse
import random
import os


def arguments_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--csv_file')
    parser.add_argument("-p", "--pid", type=int)
    parser.add_argument("-r", "--repeate", type=int, default=1)
    parser.add_argument("-c", "--change_chances", action='store_true')
    parser.add_argument("-t", "--four_types", action='store_true')
    return parser.parse_args()


def create_problem_2(pid, min_res=4, max_res=5, resources_chance=[0, 0, 0, 0]):
    line = {}
    with open(str(pid) + ".csv", 'w') as csvfile:
        fieldnames = ['Problem_ID', 'Oper_ID', "Mode_ID", "Res_ID", "Ts", "Tf", "Pre_Oper_ID"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, lineterminator = '\n')
        writer.writeheader()
        res_number = list(range(min_res, max_res + 1))
        res_weights = []
        min_res -= 1
        max_res += 1
        for num in res_number:
            val = -(num**2) + num*(min_res+max_res) - (min_res*max_res)
            val = val**2 / (val*2)
            res_weights.append(int(val))
        resources = random.choices(res_number, res_weights)[0]
        operations = random.randint(resources, resources**2)
        pre_op = ""
        line["Problem_ID"] = pid
        for operation in range(1, operations + 1):
            line["Oper_ID"] = operation
            line["Pre_Oper_ID"] = pre_op
            modes = random.randint(1, 5)
            for mode in range(1, modes + 1):
                line["Mode_ID"] = mode
                used_resources_len = 2
                used_resources = random.sample(range(1, resources + 1), used_resources_len)
                start_time = 0
                end_time = random.randint(100, 400)
                for resource in used_resources:
                    line["Res_ID"] = resource
                    line["Ts"] = start_time
                    line["Tf"] = end_time
                    writer.writerow(line)
                    start_time = random.choices([0, 0.5 * end_time, end_time, 2 * end_time], resources_chance)[0]
                    end_time = start_time + random.randint(100, 400)

            op_options = [str(op) for op in range(operation + 1)]
            op_weights = [int(100 / (operation + 1 - op))for op in range(operation + 1)]
            num_of_pre_ops = random.randint(1, max(2, int(operation / 3)))
            ops = set(random.choices(op_options, op_weights, k=num_of_pre_ops))
            if "0" in ops:
                pre_op = ""
            else:
                pre_op = ";".join(ops)


def create_problem(pid, min_res=4, max_res=10, resources_chance=[40, 20, 40], tim_chance=[50, 40, 10]):
    line = {}
    with open(str(pid) + ".csv", 'w') as csvfile:
        fieldnames = ['Problem_ID', 'Oper_ID', "Mode_ID", "Res_ID", "Ts", "Tf", "Pre_Oper_ID"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, lineterminator = '\n')
        writer.writeheader()
        res_number = list(range(min_res, max_res + 1))
        res_weights = []
        min_res -= 1
        max_res += 1
        for num in res_number:
            val = -(num**2) + num*(min_res+max_res) - (min_res*max_res)
            val = val**2 / (val*2)
            res_weights.append(int(val))
        resources = random.choices(res_number, res_weights)[0]
        operations = random.randint(resources, min(25, resources*2))
        pre_op = ""
        line["Problem_ID"] = pid
        for operation in range(1, operations + 1):
            line["Oper_ID"] = operation
            line["Pre_Oper_ID"] = pre_op
            modes = random.randint(1, max(2, int(100 / (operations * 2))))
            tim = random.randint(10 * min_res, 20 * max_res)
            for mode in range(1, modes + 1):
                line["Mode_ID"] = mode
                used_resources_len = random.randint(1, max(2, int(resources / 2))) + 1
                used_resources = random.sample(range(1, resources + 1), used_resources_len)
                start_time = 0
                end_time = random.choices([
                    random.randint(int(tim / 10), int(tim / 5)),
                    random.randint(int(tim / 5), int(tim / 2)),
                    random.randint(int(tim / 2), tim)
                    ], tim_chance)[0]
                tim_max = [False, False]
                for resource in used_resources[:-1]:
                    tim_max[1] = any(tim_max)
                    line["Res_ID"] = resource
                    line["Ts"] = start_time
                    line["Tf"] = end_time
                    writer.writerow(line)
                    duration = random.choices([
                        random.randint(min_res, int(tim / 5)),
                        random.randint(int(tim / 5), int(tim / 2)),
                        random.randint(int(tim / 2), tim)
                        ], tim_chance)[0]
                    max_start_time = tim - duration
                    if end_time > max_start_time:
                        r_chances = [40, 40, 20]
                        tim_max[0] = True
                    else:
                        max_start_time = end_time
                        r_chances = resources_chance
                    try:
                        start_time = random.choices([0, random.randint(min(1, int((max_start_time * 2) / (max_start_time + 2))), max_start_time), max_start_time], r_chances)[0]
                    except:
                        start_time = 0
                    end_time = start_time + duration
                    tim_max[0] = tim_max and (end_time / tim > 0.9)

                if not tim_max[1]:
                    line["Res_ID"] = used_resources[-1]
                    line["Ts"] = start_time
                    line["Tf"] = tim
                    writer.writerow(line)

            op_options = [str(op) for op in range(operation + 1)]
            op_weights = [int(100 / (operation + 1 - op))for op in range(operation + 1)]
            num_of_pre_ops = random.randint(1, max(2, int(operation / 3)))
            ops = set(random.choices(op_options, op_weights, k=num_of_pre_ops))
            if "0" in ops:
                pre_op = ""
            else:
                pre_op = ";".join(ops)


def main():
    args = arguments_parser()
    f = open("sql.txt", "a")
    if args.change_chances:
        resources_chances = [
            [100, 0, 0], [0, 100, 0], [0, 0, 100],
            [50, 50, 0], [50, 0, 50], [0, 50, 50],
            [70, 30, 0], [70, 0, 30], [30, 70, 0],
            [0, 70, 30], [30, 0, 70], [0, 30, 70],
            [50, 25, 25], [25, 50, 25], [25, 25, 50],
            [33, 33, 33]
        ]
        tim_chances = [
            [0, 100, 0], [0, 0, 100],
            [50, 50, 0], [50, 0, 50], [0, 50, 50],
            [70, 30, 0], [70, 0, 30], [30, 70, 0],
            [0, 70, 30], [30, 0, 70], [0, 30, 70],
            [50, 25, 25], [25, 50, 25], [25, 25, 50],
            [33, 33, 33]
        ]
    elif args.four_types:
        resources_chances = [
            [100, 0, 0, 0],
            [0, 100, 0, 0],
            [0, 0, 100, 0],
            [0, 0, 0, 100]
            #[25, 25, 25, 25]
        ]
        tim_chances = [[]]
    else:
        resources_chances = [[40, 20, 40]]
        tim_chances = [[50, 40, 10]]
    
    for r_chance in resources_chances:
        for tim_chance in tim_chances:
            for _ in range(args.repeate):
                if args.pid and tim_chance:
                    create_problem(args.pid, resources_chance=r_chance, tim_chance=tim_chance)
                    csv_file = str(args.pid) + ".csv"
                elif args.pid:
                    create_problem_2(args.pid, resources_chance=r_chance)
                    csv_file = str(args.pid) + ".csv"
                else:
                    csv_file = args.csv_file
                csv_reader = open(csv_file, mode='r')
                csv_dict = csv.DictReader(csv_reader)
                first_line = next(csv_dict)
                f.write("sql_{} = 'insert into OpMoRe values ".format(first_line["Problem_ID"]))
                f.write("({},{},{},{},{:.2f},{:.2f})".format(first_line["Problem_ID"], first_line["Oper_ID"], first_line["Mode_ID"], first_line["Res_ID"], float(first_line["Ts"]), float(first_line["Tf"])))
                for line in csv_dict:
                    f.write(",({},{},{},{},{:.2f},{:.2f})".format(line["Problem_ID"], line["Oper_ID"], line["Mode_ID"], line["Res_ID"], float(line["Ts"]), float(line["Tf"])))

                f.write("'\nc.execute(sql_{})\n".format(first_line["Problem_ID"]))
                csv_reader.close()
                csv_reader = open(csv_file, mode='r')
                csv_dict = csv.DictReader(csv_reader)
                first_line = next(csv_dict)
                f.write("sql_{} = 'insert into Priority values ".format(first_line["Problem_ID"]))
                pre_op = list(first_line["Pre_Oper_ID"].split(";"))
                first_line_pre_op = False
                if pre_op[0]:
                    operations = [first_line["Problem_ID"]]
                    first_line_pre_op = True
                    for op in pre_op:
                        f.write("({},{},{})".format(first_line["Problem_ID"], op, first_line["Oper_ID"]))

                else:
                    operations = []

                for line in csv_dict:
                    if line["Oper_ID"] not in operations:
                        pre_op = list(line["Pre_Oper_ID"].split(";"))
                        if pre_op[0]:
                            operations.append(line["Oper_ID"])
                            for op in pre_op:
                                if first_line_pre_op:
                                    f.write(",({},{},{})".format(line["Problem_ID"], op, line["Oper_ID"]))
                                else:
                                    f.write("({},{},{})".format(line["Problem_ID"], op, line["Oper_ID"]))
                                    first_line_pre_op = True

                f.write("'\nc.execute(sql_{})\n".format(first_line["Problem_ID"]))
                csv_reader.close()
                if args.pid:
                    os.remove(csv_file)
                    args.pid += 1
    f.close()


if __name__ == '__main__':
    main()
