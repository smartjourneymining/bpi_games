import argparse
import networkx as nx

parser = argparse.ArgumentParser(
                    prog = 'decision_boundary_reduction',
                    description = "Merges determined states together to results in one guaranteed positive outcome state and one guaranteed negative outcome state.",)
parser.add_argument('input', help = "Input model")
parser.add_argument('output', help = "Output path for reduced game") 
parser.add_argument('-s', '--strict', help = "Game decision boundary with neglecting game properties (strict decision boundary); default = False", type = bool, default = False) 

args = parser.parse_args()

# Uses the decision boundary as model reduction
def reduce_graph(g):
    pos_cluster = []
    neg_cluster = []
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

    g.nodes["pos"]['viz'] = {'color': {'r': 0, 'g': 255, 'b': 0, 'a': 0}, 'position' : {'x' : 0.0, 'y': 0.0, 'z': 0.0}}
    g.nodes["neg"]['viz'] = {'color': {'r': 255, 'g': 0, 'b': 0, 'a': 0}, 'position' : {'x' : 0.0, 'y': 0.0, 'z': 0.0}}

    g.nodes["neg"]["final"] = True
    g.nodes["pos"]["final"] = True

    for s in g:
        if "final" not in g.nodes[s]:
             g.nodes[s]["final"] = False
   
    g.remove_edges_from(nx.selfloop_edges(g))

    return g

def db_reduction(g):

    #pos_cluster = set()
    #neg_cluster = set()

    positive_cluster = []
    for s in g.nodes:
        if g.nodes[s]['results']:
            g.nodes[s]['color'] = "green"
            positive_cluster.append(s)

    # attempted merge:
    negative_cluster = []
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
            negative_cluster.append(s)
    """
    for s in g.nodes:
        for neighbour in g[s]:
            reaches_pos = False
            reaches_neg = False
            sub_nodes = set(list(nx.descendants(g, neighbour)))
            sub_nodes.add(neighbour)
            for s1 in sub_nodes:
                if 'negative' in s1:
                    reaches_neg = True
            for s1 in sub_nodes:
                if 'positive' in s1:
                    reaches_pos = True
            # reaches exactly one of both outcomes
            if(reaches_neg and not reaches_pos or reaches_pos and not reaches_neg):
                if reaches_neg:
                    neg_cluster.update(sub_nodes)
                else:
                    pos_cluster.update(sub_nodes)
    """

    for s in positive_cluster:
        g = nx.contracted_nodes(g, "pos", s)
    for s in negative_cluster:
        g = nx.contracted_nodes(g, "neg", s)
    g.nodes['pos']['decision_boundary'] = False
    g.nodes['neg']['decision_boundary'] = False

    g.nodes["pos"]['viz'] = {'color': {'r': 0, 'g': 255, 'b': 0, 'a': 0}, 'position' : {'x' : 0.0, 'y': 0.0, 'z': 0.0}}
    g.nodes["neg"]['viz'] = {'color': {'r': 255, 'g': 0, 'b': 0, 'a': 0}, 'position' : {'x' : 0.0, 'y': 0.0, 'z': 0.0}}

    g.nodes["neg"]["final"] = True
    g.nodes["pos"]["final"] = True

    for s in g:
        if "final" not in g.nodes[s]:
             g.nodes[s]["final"] = False

    g.remove_edges_from(nx.selfloop_edges(g))
    

    """
    # decide if edge to pos / neg cluster is controllable
    for e in g.edges:
        if e[1] == "pos":
            if 'contraction' in g.edges[e]:
                for e1 in g.edges[e]['contraction']:
                    assert(e1[0] == e[0])
                # one controllable - can print controllable edge
                if any([g.edges[e]['contraction'][e1]['controllable'] for e1 in g.edges[e]['contraction']]): 
                    g.edges[e]['controllable'] = True
        elif e[1] == "neg":
            if 'contraction' in g.edges[e]:
                for e1 in g.edges[e]['contraction']:
                    assert(e1[0] == e[0])
                for e1 in g.edges[e]['contraction']:
                    if "TIMEOUT" in g.edges[e]['contraction'][e1]['action']:
                        g.edges[e]['action'] = 'TIMEOUT'
                # one uncontrollable - have to print uncontrollable edge
                if (any([not g.edges[e]['contraction'][e1]['controllable'] for e1 in g.edges[e]['contraction']])): 
                    g.edges[e]['controllable'] = False
        else:
            assert(not 'contraction' in g.edges[e])
    """


    

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