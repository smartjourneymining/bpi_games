import subprocess

max = 10
out = "/home/paul/Documents/bpi_games/cli/"
activities_file = "activities.xml"
uppaal_path = "/home/paul/Downloads/uppaal-4.1.20-stratego-9-linux64/bin/verifyta"
#output = subprocess.call(["python3",  "log_parser.py", '/home/paul/Documents/bpi_games/BPI Challenge 2017.xes', out])

#print(output)

for i in range(3,4):
    #output = subprocess.Popen(["python3", "process_model.py", "/home/paul/Documents/bpi_games/cli/bpic2017_after.xes", out, "-hist" , str(i)], stdout=subprocess.PIPE)
    #output.wait()
    #file_name = str(output.communicate()[0]).replace("\\n'", '').split("Generated: ")[-1]
    #print(file_name)

    file_name = '/home/paul/Documents/bpi_games/cli/PMODEL_input:bpic2017_after_type:sequence_history:3.gexf'
    output = subprocess.Popen(["python3", "build_game.py", file_name, out, activities_file], stdout=subprocess.PIPE)
    output.wait()
    file_name = str(output.communicate()[0]).replace("\\n'", '').split("Generated: ")[-1]
    print(file_name)

    output = subprocess.Popen(["python3", "decision_boundary.py", file_name, out, uppaal_path], stdout=subprocess.PIPE)
    output.wait()
    file_name = str(output.communicate()[0]).replace("\\n'", '').split("Generated: ")[-1]
    print(file_name)

    output = subprocess.Popen(["python3", "decision_boundary_reduction.py", file_name, out], stdout=subprocess.PIPE)
    output.wait()
    file_name = str(output.communicate()[0]).replace("\\n'", '').split("Generated: ")[-1]
    print(file_name)

print("done")