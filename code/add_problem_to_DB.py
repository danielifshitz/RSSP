import csv
import argparse


def arguments_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--csv_file', required=True)
    return parser.parse_args()

def main():
    args = arguments_parser()
    f = open("sql.txt", "a")

    csv_dict = csv.DictReader(open(args.csv_file, mode='r'))
    first_line = next(csv_dict)
    f.write("sql_{} = 'insert into OpMoRe values ".format(first_line["Problem_ID"]))
    f.write("({},{},{},{},{:.2f},{:.2f})".format(first_line["Problem_ID"], first_line["Oper_ID"], first_line["Mode_ID"], first_line["Res_ID"], float(first_line["Ts"]), float(first_line["Tf"])))
    for line in csv_dict:
        f.write(",({},{},{},{},{:.2f},{:.2f})".format(line["Problem_ID"], line["Oper_ID"], line["Mode_ID"], line["Res_ID"], float(line["Ts"]), float(line["Tf"])))

    f.write("'\nc.execute(sql_{})\n".format(first_line["Problem_ID"]))

    csv_dict = csv.DictReader(open(args.csv_file, mode='r'))
    first_line = next(csv_dict)
    f.write("sql_{} = 'insert into Priority values ".format(first_line["Problem_ID"]))
    pre_op = list(first_line["Pre_Oper_ID"].split(";"))
    first_line_pre_op = False
    if pre_op[0]:
        operations = [first_line["Problem_ID"]]
        first_line_pre_op = True
        for op in pre_op:
            f.write("({},{},{})".format(first_line["Problem_ID"], first_line["Oper_ID"], op))

    else:
        operations = []
    
    for line in csv_dict:
        if line["Oper_ID"] not in operations:
            pre_op = list(line["Pre_Oper_ID"].split(";"))
            if pre_op[0]:
                operations.append(line["Oper_ID"])
                for op in pre_op:
                    if first_line_pre_op:
                        f.write(",({},{},{})".format(line["Problem_ID"], line["Oper_ID"], op))
                    else:
                        f.write("({},{},{})".format(line["Problem_ID"], line["Oper_ID"], op))
                        first_line_pre_op = True


    f.write("'\nc.execute(sql_{})\n".format(first_line["Problem_ID"]))
    f.close()

            

if __name__ == '__main__':
    main()