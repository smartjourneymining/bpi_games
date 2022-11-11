import subprocess

max_sequence = 10
max_unrolling = 10
out = "/home/paul/Documents/bpi_games/cli/"
activities_file = "activities.xml"
uppaal_path = "/home/paul/Downloads/uppaal-4.1.20-stratego-9-linux64/bin/verifyta"
timeout = 180

output = subprocess.call(["python3",  "log_parser.py", '/home/paul/Documents/bpi_games/BPI Challenge 2017.xes', out])

for i in range(3,4):
    try: 
        output = subprocess.check_output(["python3", "process_model.py", "/home/paul/Documents/bpi_games/cli/bpic2017_before.xes", out, "-hist" , str(i)], timeout=timeout)
        file_name = str(output).replace("\\n'", '').split("Generated: ")[-1]
        print(file_name)

        output = subprocess.check_output(["python3", "build_game.py", file_name, out, activities_file], timeout=timeout)
        file_name = str(output).replace("\\n'", '').split("Generated: ")[-1]
        print(file_name)

        unrolled_model_name = file_name
        for k in range(1,4):
            try:
                output = subprocess.check_output(["python3", "decision_boundary.py", unrolled_model_name, out, uppaal_path, "-k", str(k)], timeout=timeout)
                file_name = str(output).replace("\\n'", '').split("Generated: ")[-1]
                print(file_name)

                output = subprocess.check_output(["python3", "decision_boundary_reduction.py", file_name, out], timeout=timeout)
                file_name = str(output).replace("\\n'", '').split("Generated: ")[-1]
                print(file_name)

            except subprocess.TimeoutExpired:
                print("Timeout - continue now")
                continue

        
    except subprocess.TimeoutExpired:
        print("Timeout - continue now")
        continue
print("done")