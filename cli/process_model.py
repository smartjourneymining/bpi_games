import argparse
from pm4py.objects.log.importer.xes import importer as xes_importer
import networkx as nx
import json 
import numpy as np 
#from datetime import datetime

parser = argparse.ArgumentParser(
                    prog = 'process_model',
                    description = "Takes an processed event log as input and computes a directly-follows process model with weights.",)
parser.add_argument('input', help = "Input event log") 
parser.add_argument('output', help = "Output path for process model") 
parser.add_argument('-t', '--type', help = "Type of directly follows model: default = hist", default = "sequence", choices = ["sequence", "multiset"]) 
parser.add_argument('-hist', '--history', help = "Number of past steps to be included; default = 3", default = 3, type = int) 

args = parser.parse_args()

# Concats the trace to a multiset-history
def ms(trace):
    multiset = {}
    for pos in trace:
        if pos['concept:name'] not in multiset:
            multiset[pos['concept:name']] = 1
        else:
            multiset[pos['concept:name']] += 1
    return json.dumps(multiset, sort_keys=True).encode() # use json encodings for multisets

# Computes the sequence-history of the given trace
def sequence(trace): 
    hist = str(trace[0]['concept:name'])
    for pos in trace[1:]:
        hist += " - " + str(pos['concept:name']) # construct history
    return hist

# Function to compute a transition system, given a pre-processed log
def transition_system(log, history, abstraction):
    edges = []
    edge_counter = {}
    controll = {}
    action = {}
    edge_mapping = {}
    for trace_index in range(len(log)):
        trace = log[trace_index]
        s = "start"
        assert(trace[0]['concept:name']=="start")
        for pos_index in range(1,len(trace)):
            pos = trace[pos_index]
            activity = pos['concept:name']
            #t = ms(trace[max(0,pos_index-history+1):pos_index+1])
            t = abstraction(trace[max(0,pos_index-history+1):pos_index+1])
            e = (s,t)
            action[e] = activity
            if e not in edges:
                edges.append(e)
                edge_counter[e] = 1
                edge_mapping[e] = [trace_index]
            else:
                edge_counter[e] = edge_counter[e]+1
                edge_mapping[e].append(trace_index)
            s = t
    g = nx.DiGraph()
    for e in edges:
        g.add_edge(e[0], e[1])
    to_remove = [] # to remove selve-loops
    for e in g.edges:
        if e[0] == e[1]:
            to_remove.append(e)
        # set properties
        g[e[0]][e[1]]['action'] = action[e]

    for e in to_remove:
        if e in g.edges():
            g.remove_edge(e[0],e[1])
    
    return g, edge_mapping

# compute weights
def isInTrace(s,t, trace):
    for i in range(len(trace)-1):
        if trace[i]['concept:name'] == s and trace[i+1]['concept:name'] == t:
            return True
    return False

def weight(trace):
    return 1 if any("positive" in pos['concept:name'] for pos in trace) else -1

def entropy(p1, p2):
    if p1 == 0 or p2 == 0:
        return 0
    return - p1*np.log2(p1) - p2* np.log2(p2)

def distribution(s,t,log, edge_mapping):
    distr = {1.0: 0 , -1.0 : 0}
    assert((s,t) in edge_mapping)
    for trace_index in edge_mapping[(s,t)]:
        w = weight(log[trace_index])
        distr[w] += 1 #
    return distr[1], distr[-1]

def compute_edge_cost(g, traces, edge_mapping):
    edge_cost = {}
    counter = 1
    for s in g.nodes:
        counter +=1
        for t in g[s]:

            
            p1, p2 = distribution(s,t,traces, edge_mapping)
            w = 1 if p1 >= p2 else -1

            wp1 = p1/(p1+p2)
            wp2 = p2/(p1+p2)

            scaling = 20
            entro = entropy(wp1, wp2)

            edge_cost[(s,t)] = (((1-entro) * w) -0.21 )*scaling

    return edge_cost

def annotate_graph(g, edge_cost):
    for e in edge_cost:
        g[e[0]][e[1]]['cost'] = round(edge_cost[e],2)
    return g

def add_traversal_information(g, edge_mapping):
    for e in g.edges:
        g.edges[e]['edge_traversal'] = len(edge_mapping[e])

    for s in g:
        if s not in ["start"] and "pos" not in s and "neg" not in s:
            assert(sum( [g.edges[e]['edge_traversal'] for e in g.in_edges(s)] ) == sum( [g.edges[e]['edge_traversal'] for e in g.out_edges(s)] ))
        outgoing_sum = sum( [g.edges[e]['edge_traversal'] for e in g.out_edges(s)] )
        if "pos" in s or "neg" in s:
            outgoing_sum = sum( [g.edges[e]['edge_traversal'] for e in g.in_edges(s)] ) # change to ingoing sum
        g.nodes[s]['node_traversal'] = outgoing_sum

    return g

log = xes_importer.apply(args.input)

system, edge_mapping = transition_system(log, args.history, ms if args.type == "multiset" else sequence)
edge_cost = compute_edge_cost(system, log, edge_mapping)

g = annotate_graph(system, edge_cost)

g = add_traversal_information(g, edge_mapping)

name = args.output + "PMODEL" + "_" + "input:"+ args.input.split("/")[-1].split(".")[0]  + "_" + "type:" + args.type + "_"+ "history:"+ str(args.history) + '.gexf'
# "_" + datetime.today().strftime('%Y-%m-%d#%H:%M:%S')
# not sure if datetime needed
nx.write_gexf(g, name) 
print("Generated:", name)