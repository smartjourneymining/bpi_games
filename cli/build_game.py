import argparse
from pm4py.objects.log.importer.xes import importer as xes_importer
import networkx as nx
import json 

parser = argparse.ArgumentParser(
                    prog = 'build_game',
                    description = "Transforms a directly follows model produces by 'process_model.py' into a game by annotating (un)controllable actions.",)
parser.add_argument('-i', '--input', help = "Input model", required = True)
parser.add_argument('-o', '--output', help = "Output path for game", required = True) 
parser.add_argument('-a', '--activities', help = "JSON-file storing controllability of edges.", required = True) 

args = parser.parse_args()

g = nx.read_gexf(args.input)

with open(args.activities) as f:
    data = f.read()
actors = json.loads(data)
keys = list(actors.keys())

for e in g.edges:
    controllable_set = False
    for key in actors:
        if key in g.edges[e]['action']:
            controllable_set = True
            g.edges[e]['controllable'] = actors[key] == 'company'
    if not controllable_set:
        g.edges[e]['controllable'] = True

nx.write_gexf(g, args.output + "GAME" + args.input.split("/")[-1].split(".")[0].split("PMODEL")[-1] + "_" + "actors:" + args.activities.split("/")[-1]+'.gexf')