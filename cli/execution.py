import subprocess
import argparse
import networkx as nx

parser = argparse.ArgumentParser(
                    prog = 'group_execution',
                    description = "Support tool to build decision boundaries with different ranges of histories and unrollings.",)
parser.add_argument('input', help = "Preprocessed input event log")
parser.add_argument('output', help = "Output path for reduced game")
parser.add_argument('activities', help = "Activities to construct game")
parser.add_argument('uppaal_stratego', help = "Path to Uppaal Stratego's VERIFYTA")
parser.add_argument('-hist', '--max_history', help = "Maximum sequence to be tested", type = int, required = True)
parser.add_argument('-k', '--max_unrolling_factor', help = "Maximum Constant factor for how often every lop is unrolled", type = int, default = 1) 
parser.add_argument('-time', '--timeout', help = "Maximum sequence to be tested", default = 180, type = int)
parser.add_argument('-t', '--type', help = "Type of directly follows model: default = hist", default = "sequence", choices = ["sequence", "multiset"])
parser.add_argument('-min_hist', '--min_history', help = "Sequence to be started with", type = int, default = 1)
parser.add_argument('-min_k', '--min_unrolling_factor', help = "Minimum Constant factor for how often every lop is unrolled", type = int, default = 1) 

args = parser.parse_args()


decision_boundary = {}
for i in range(args.min_history,args.max_history+1):
    try: 
        output = subprocess.check_output(["python3", "process_model.py", args.input, args.output, "-t", str(args.type), "-hist" , str(i)], timeout=args.timeout)
        file_name = str(output).replace("\\n'", '').split("Generated: ")[-1]
        print(file_name)

        output = subprocess.check_output(["python3", "build_game.py", file_name, args.output, args.activities], timeout=args.timeout)
        file_name = str(output).replace("\\n'", '').split("Generated: ")[-1]
        print(file_name)

        unrolled_model_name = file_name
        for k in range(args.min_unrolling_factor,args.max_unrolling_factor+1):
            try:
                output = subprocess.check_output(["python3", "decision_boundary.py", unrolled_model_name, args.output, args.uppaal_stratego, "-k", str(k)], timeout=args.timeout)
                file_name = str(output).replace("\\n'", '').split("Generated: ")[-1]
                print(file_name)

                output = subprocess.check_output(["python3", "decision_boundary_reduction.py", file_name, args.output], timeout=args.timeout)
                file_name = str(output).replace("\\n'", '').split("Generated: ")[-1]
                print(file_name)

                g = nx.read_gexf(file_name)
                db = [n for n in g if 'decision_boundary' in g.nodes[n] and g.nodes[n]['decision_boundary']]
                decision_boundary[str(file_name)] = db
            except subprocess.TimeoutExpired:
                print("Timeout - abort further unrolling")
                break

        
    except subprocess.TimeoutExpired:
        print("Timeout - continue now")
        continue
for n in decision_boundary:
    print(n, "(", len(decision_boundary[n]), "):")
    for e in decision_boundary[n]:
        print("      ", e)