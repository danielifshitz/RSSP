import csv
import argparse
from job import Job
from sqlite3 import connect


def arguments_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--csv_file')
    parser.add_argument('-p', '--pids', nargs='+')
    return parser.parse_args()

def main(pids, csv_file):
    for pid in pids:
        job = Job(pid)
        conn = connect('data.db')
        c = conn.cursor()
        c.execute(f"SELECT DISTINCT Solution_type FROM Solution where Problem_ID = {pid}")
        solution_types = c.fetchall()
        op_csv = open(str(pid) + "_op.csv", 'w')
        res_csv = open(str(pid) + "_res.csv", 'w')
        op_fieldnames = ['Problem_ID', 'Greedy', "Operation_ID", "Mode_ID", "Ti", "Rim", "num_succesors", "delta"]
        res_fieldnames = ['Problem_ID', 'Greedy', "Resource_ID", "Operation_ID", "Start_time", "Finish_time"]
        op_writer = csv.DictWriter(op_csv, fieldnames=op_fieldnames, lineterminator='\n')
        op_writer.writeheader()
        res_writer = csv.DictWriter(res_csv, fieldnames=res_fieldnames, lineterminator='\n')
        res_writer.writeheader()
        for (solution_type,) in solution_types:
            c.execute(f"SELECT Problem_ID, Oper_ID, Mode_ID, Ts FROM Solution where Problem_ID = {pid} and Solution_type = '{solution_type}'")
            query = c.fetchall()
            op_lines = {}
            res_space = {}
            op_tim_end = {}
            for (problem_id, op_id, mode_id, Ts) in query:
                res_data = job.get_Trs_and_Trf(str(op_id), str(mode_id), Ts)
                op_tim_end[op_id] = job.operations[str(op_id)].get_mode_by_name(str(mode_id)).tim + Ts
                for res_line in res_data:
                    if res_line["Resource_ID"] not in res_space:
                        res_space[res_line["Resource_ID"]] = []

                    res_space[res_line["Resource_ID"]].append({"Operation_ID": op_id,
                                                               "Start_time": res_line["Start_time"],
                                                               "Finish_time": res_line["Finish_time"]})

                    res_line.update({'Problem_ID': problem_id, 'Greedy': solution_type})
                    res_writer.writerow(res_line)

                op_lines[op_id] = {'Problem_ID': problem_id, 'Greedy': solution_type, "Operation_ID": op_id,
                                   "Mode_ID": mode_id, "Ti": Ts}

            c.execute(f"SELECT Solution FROM BestSolution where Problem_ID = {pid} and Solution_type = '{solution_type}'")
            solution = c.fetchall()[0][0]
            op_space = {}
            for op, next_ops in job.suc_list_after_remove.items():
                op_space[int(op)] = float("inf")
                for next_op in next_ops:
                    op_space[int(op)] = min(op_lines[int(next_op)]["Ti"] - op_tim_end[int(op)], op_space[int(op)])

            for res in res_space.values():
                res.sort(key=lambda element: element["Start_time"])
                for res1, res2 in zip(res[:], res[1:]):
                    op_space[res1["Operation_ID"]] = min(res2["Start_time"] - res1["Finish_time"], op_space[res1["Operation_ID"]])

                op_space[res[-1]["Operation_ID"]] = min(solution - res[-1]["Finish_time"], op_space[res[-1]["Operation_ID"]])

            for op_num, op_line in op_lines.items():
                op_line.update({"Rim": len(job.operations[str(op_num)].get_mode_by_name(str(op_line["Mode_ID"])).resources),
                                "num_succesors": len(job.suc_list_after_remove[str(op_num)]), "delta": op_space[op_num]})
                op_writer.writerow(op_line)

        op_csv.close()
        res_csv.close()


if __name__ == '__main__':
    args = arguments_parser()
    main(args.pids, args.csv_file)
