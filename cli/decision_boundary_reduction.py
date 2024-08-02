import argparse
import networkx as nx

parser = argparse.ArgumentParser(
                    prog = 'decision_boundary_reduction',
                    description = "Merges determined states together to results in one guaranteed positive outcome state and one guaranteed negative outcome state.",)
parser.add_argument('input', help = "Input model")
parser.add_argument('output', help = "Output path for reduced game") 
parser.add_argument('-s', '--static', help = "Game decision boundary with neglecting game properties (static decision boundary); default = False", type = bool, default = False) 

args = parser.parse_args()

# Uses the decision boundary computation as model reduction
def db_reduction(g):

    pos_cluster = []
    neg_cluster = []

    if not args.static:
        for s in g.nodes:
            if g.nodes[s]['positive_guarantee']:
                g.nodes[s]['color'] = "green"
                pos_cluster.append(s)

        for s in g.nodes:
            reachable = set(list(nx.descendants(g, s)))
            reaches_pos = False
            for neighbour in reachable:
                if "pos" in neighbour:
                    reaches_pos = True
            if "pos" in s:
                reaches_pos = True
            if not reaches_pos:
                g.nodes[s]['color'] = "red"
                neg_cluster.append(s)
    else:
        for s in g:
            subgraph = nx.subgraph(g, set(list(nx.descendants(g, s))))
            subgraph = nx.DiGraph(subgraph)
            nodes = [s for s in subgraph]
            sub_results = [g.nodes[n]["positive_guarantee"] for n in nodes if 'positive_guarantee' in g.nodes[n]]
            if len(set(sub_results))<2:
                # sub_results has size 0 or 1: 0 if end node, 1 else
                if g.nodes[s]["positive_guarantee"]:
                    pos_cluster.append(s)
                else:
                    neg_cluster.append(s)

    for s in pos_cluster:
        g = nx.contracted_nodes(g, "pos", s)
    for s in neg_cluster:
        g = nx.contracted_nodes(g, "neg", s)
    g.nodes['pos']['decision_boundary'] = False
    g.nodes['neg']['decision_boundary'] = False
    g.nodes['pos']['positive_guarantee'] = True
    g.nodes['neg']['positive_guarantee'] = False

    g.nodes["pos"]['viz'] = {'color': {'r': 0, 'g': 255, 'b': 0, 'a': 0}, 'position' : {'x' : 0.0, 'y': 0.0, 'z': 0.0}}
    g.nodes["neg"]['viz'] = {'color': {'r': 255, 'g': 0, 'b': 0, 'a': 0}, 'position' : {'x' : 0.0, 'y': 0.0, 'z': 0.0}}

    g.nodes["neg"]["final"] = True
    g.nodes["pos"]["final"] = True

    for s in g:
        if "final" not in g.nodes[s]:
             g.nodes[s]["final"] = False

    g.remove_edges_from(nx.selfloop_edges(g))
   

    return g

# Load graph
g = nx.read_gexf(args.input)

#g = reduce_graph(g)
g = db_reduction(g)

# add graph attributes
g.graph["reduced_graph"] = True

print(g.graph["reduced_graph"])
name = args.output + args.input.split("/")[-1].split(".")[0] + "reduced:True"+ ".gexf"
nx.write_gexf(g, name)
print("Generated:", name)