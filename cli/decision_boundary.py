import argparse
import networkx as nx
import copy 
import subprocess

parser = argparse.ArgumentParser(
                    prog = 'decision_boundary',
                    description = "Computes the decision boundary of the given game.",)
parser.add_argument('input', help = "Input model")
parser.add_argument('output', help = "Output path for game with annotated decision boundary")
parser.add_argument('uppaal_stratego', help = "Path to Uppaal Stratego's VERIFYTA") 
parser.add_argument('-d', '--debug', help = "Print additional information", default = False) 
parser.add_argument('-q', '--query', help = "Path to the boolean query for the decision boundary.", default = 'guaranteed_tool.q')
parser.add_argument('-k', '--unrolling_factor', help = "Constant factor how often every lop is unrolled; default = 0", type = int, default = 0) 
parser.add_argument('-s', '--static', help = "Game decision boundary with neglecting game properties (static decision boundary); default = False", type = bool, default = False) 

args = parser.parse_args()

# Computes all possible shift of lists
def shifted_lists(l):
    shifted_lists = []
    for j in range(len(l)):
        list_constructed = copy.deepcopy(l[j:])
        list_constructed.extend(l[:j])
        list_constructed.append(list_constructed[0])
        shifted_lists.append(list_constructed)
    return shifted_lists

# checks if history hist contains circle c
def contains(hist, c):
    n = len(c)+1
    max_count = 0
    lists = shifted_lists(c)
    for helper_list in lists:
        count = 0
        for i in range(len(hist)-(n-1)):
            if hist[i:i+n] == helper_list:
                count += 1
        max_count = max(max_count, count)
    return max_count

# returns true if edge (e,v) is on c
def is_on(e,v,c):
    for i in range(len(c)-1):
        if c[i] == e and c[i+1] == v:
            return True
    if c[-1] == e and c[0] == v:
        return True
    
# Presented Unrolling algorithm, Algorithm 1 with online reducing
def unroll(G, start, target, k, debug = args.debug):
    G_gen = nx.DiGraph()
    G_gen.add_node(start, hist = [str(start)])
    if 'controllable' in G.nodes[start]:
        G_gen.nodes[start]["controllable"] = G.nodes[start]["controllable"]

    cycles = list(nx.simple_cycles(G))

    queue = [start]
    # start bf-search
    while(queue):
        if debug:
            print(len(G_gen.nodes), len(queue))
        s = queue[0]
        queue.pop(0)
        s_original = str(s).split(".")[0]
        neighbours = list(G[s_original])
        for t in neighbours:
            t_original = t
            local_hist = copy.deepcopy(G_gen.nodes[s]["hist"])
            local_hist.append(str(t_original))
            is_on_cycle = False
            can_traverse = False
            path = []
            circle = []
            relevant_cycle = []
            for c in cycles:
                if is_on(s_original,t_original,c):
                    relevant_cycle.append(c)
                    
            all_smaller = True
            for c in relevant_cycle:
                if contains(local_hist,c) >= k:
                    all_smaller = False
            
            if not all_smaller:
                paths = list(nx.all_simple_paths(G, source=t, target=target))
                for p in paths:
                    merged_hist = copy.deepcopy(local_hist)
                    merged_hist.extend(p[1:]) # 1.st element already added
                    can_not_traverse = False
                    
                    #test if no loop larger than k with path
                    for c_loop in relevant_cycle:
                        if contains(merged_hist,c_loop) > k : # check that there is path without completing additional cycle
                            can_not_traverse = True
                    can_traverse = not can_not_traverse
            if all_smaller or can_traverse:               
                #every node not on cycle can be unqiue ("merge point" within unrolled graph)
                if relevant_cycle:
                    while t in G_gen.nodes:
                        if "." not in t:
                            t += ".1"
                        else:
                            t = t.split(".")[0]+"."+str(int(t.split(".")[-1])+1)
                # add node t only to graph if not already treated

                if t not in queue:
                    queue.append(t)
                    G_gen.add_node(t, hist = local_hist)
                assert(s in G_gen and t in G_gen)
                G_gen.add_edge(s,t)
                if('cost' in G[s_original][t_original]):
                    G_gen[s][t]['cost'] = G[s_original][t_original]['cost']
                if('controllable' in G[s_original][t_original]):
                    G_gen[s][t]['controllable'] = G[s_original][t_original]['controllable']

    return G_gen

# construction of uppaal model (write model into upaal file)
def to_uppaal(g, name, layout = "sfdp", debug = args.debug):
    f = open(name, "w+")
    
    pos = nx.drawing.nx_agraph.graphviz_layout(g, prog=layout, args='-Grankdir=LR')

    f.write('<?xml version="1.0" encoding="utf-8"?>')
    f.write("<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' 'http://www.it.uu.se/research/group/darts/uppaal/flat-1_1.dtd'>")
    f.write('<nta>')
    f.write('<declaration>')
    f.write('int e = 0;')
    f.write('\n'+'clock x;')
    f.write('\n'+'hybrid clock t;')
    f.write('\n'+'int steps;')
    f.write('\n'+'bool reached_positive = false;')
    f.write('\n'+'bool reached_negative = false;')
    f.write('\n'+'int final_gas = -1;')
    f.write('</declaration>')
    f.write('<template>')
    f.write('<name x="5" y="5">Template</name>')
    
    # print locations
    ids = {}
    for s,i in zip(pos, range(len(pos))):
        ids[s] = i
        print_location(f, "id"+str(i),pos[s][0],pos[s][1],s)
        f.write('\n')
                    
    f.write('<init ref="id'+str(ids['start'])+'"/>')
    
    for e in g.edges:
        assert("cost" in g[e[0]][e[1]] and "controllable" in g[e[0]][e[1]])
        print_edge(f, ids[e[0]], ids[e[1]], pos[e[0]], pos[e[1]], g[e[0]][e[1]]['cost'], g[e[0]][e[1]]['controllable'], e, g)

    f.write('</template>')
    f.write('<system>')
    f.write('Journey = Template();')
    f.write('system Journey;')
    f.write('</system>')
    f.write('</nta>')
    f.close()
    if debug:
        print("all written to", f.name)

def print_location(f, location_id, x, y, name):
    name = str(name)
    name = name.replace('"', '-')
    name = name.replace('{', '')
    name = name.replace('}', '')
    name = name.replace("'", '-')
    name = name.replace("_", '')
    name = name.replace("(", '')
    name = name.replace(")", '')
    f.write('<location id="'+location_id+'" x="'+str(int(x))+'" y="'+str(int(y))+'">')
    f.write('<name x="'+str(int(x))+'" y="'+str(int(y)+20)+'">'+str(name).replace(":", "").replace(" ","").replace(".", "").replace(",", "").replace("-","")+'</name>')
    f.write('<label kind="invariant" x="'+str(int(x))+'" y="'+str(int(y)-30)+'">')
    if "positive" not in name and "negative" not in name and "outOfGas" not in name:
        f.write('x &lt;= ' + str(2))
    else:
        f.write("t'==0")
    f.write('</label>')
    f.write('</location>')

def print_edge(f, s, t, pos_s, pos_t, w, controllable, e, g, guard = False):
    x = (pos_s[0]+pos_t[0])/2
    y = (pos_s[1]+pos_t[1])/2
    if controllable:
        f.write('<transition action = "">')
    else:
        f.write('<transition controllable="false" action = "">')
    f.write('<source ref="id'+str(s)+'"/>')
    f.write('<target ref="id'+str(t)+'"/>')
        
    f.write('<label kind="assignment" x="'+str(int(x))+'" y="'+str(int(y))+'">')
    f.write(' steps += 1')
    f.write(',\n'+ 'x = 0')
    if "positive" in str(e[1]):
        f.write(',\n'+ 'reached_positive = true')
        f.write(',\n'+ 'final_gas = e +'+str(int(round(w))))
    elif "negative" in str(e[1]):
        f.write(',\n'+ 'reached_negative = true')
        f.write(',\n'+ 'final_gas = e + '+str(int(round(w))))
        
    f.write(',\n'+'e = e + '+str(int(round(w))))
    f.write('</label>')
    
    f.write('</transition>')

# Computes mapping R from alg. 1
# Return results too for easier handling
def query(g, query_path):
    # partial graph implications, per activity
    results = {}
    
    assert('start' in g)
    dfs_numbers = {}

    for n,i in zip(nx.dfs_postorder_nodes(g, 'start'), range(len(g.nodes)-1)):
        dfs_numbers[i] = n
    dfs_numbers[len(g.nodes)-1] = 'start'

    for i in range(len(g.nodes)):
    #for a in g.nodes:
        assert(i in dfs_numbers)
        current_state = dfs_numbers[i]

        sub_nodes = set()
        sub_nodes.update(set(list(nx.descendants(g, current_state))))
        sub_nodes.add(current_state) # cant assume that all sub_nodes are contained due to loops

        all_neighbours_contained = True
        neighbour_results = []
        for n in g[current_state]:
            if n not in results:
                all_neighbours_contained = False
                break
            neighbour_results.append(results[n])

        all_leaves_computed = True
        leave_results = []
        for s in sub_nodes:
            if g.out_degree(s) == 0 and s != current_state:
                if s not in results:
                    all_leaves_computed = False
                    break
                leave_results.append(results[s])
        
        # can set results if all neighbours are contained
        if all_neighbours_contained and len(set(neighbour_results))==1:
            results[current_state] =  neighbour_results[0]# write to assign result if determined
            g.nodes[current_state]["positive_guarantee"] = neighbour_results[0]
            continue
        
        # can set result by reachable leaves
        if all_leaves_computed and len(set(leave_results)) == 1:
            results[current_state] = leave_results[0]
            g.nodes[current_state]["positive_guarantee"] = leave_results[0]
            continue

        """
        states = [a]

        sub_nodes = set()
        for s in states:
            sub_nodes.update(set(list(nx.descendants(g, s))))
            sub_nodes.add(s)
        if len(sub_nodes) > args.threshold_reachable_nodes: # execute only on nodes with less than threshold descendants for better performance
            continue

        """
        subgraph = nx.subgraph(g, sub_nodes)
        subgraph = nx.DiGraph(subgraph)

        # add start node to subgraph
        start_nodes = []
        for n in subgraph.nodes:
            if subgraph.in_degree(n) == 0:
                start_nodes.append(n)
        for n in start_nodes:
            subgraph.add_edge("start", n)
            subgraph["start"][n]["controllable"] = True
            subgraph["start"][n]["cost"] = 0
        # if initial node lies on cycle, per default set as start node
        if "start" not in subgraph.nodes:
            subgraph.add_edge("start", current_state)
            subgraph["start"][current_state]["controllable"] = True
            subgraph["start"][current_state]["cost"] = 0

        if args.debug:
            nx.write_gexf(subgraph, args.output+"test.gexf")
            to_uppaal(subgraph, args.output+'bpi2017subgraph.xml')
        target = [s for s in subgraph.nodes if "positive" in s or "negative" in s]
        subgraph_unrolled = unroll(subgraph, "start", target, args.unrolling_factor)
        positives = []
        for s in subgraph_unrolled.nodes:
            if "positive" in s:
                positives.append(s)
        #assert(len(positives) <= 1)
        to_uppaal(subgraph_unrolled, args.output+'bpi2017subgraph.xml')
        out = subprocess.Popen([args.uppaal_stratego, args.output+'bpi2017subgraph.xml', query_path], stdout=subprocess.PIPE)
        result = "is satisfied" in str(out.communicate()[0])
        results[current_state] = result

        g.nodes[current_state]["positive_guarantee"] = result
    

    return g, results

# Function to compute clusters for decision boundary
def reachable_cluster(g, results):
    pos_cluster = []
    neg_cluster = []
    g_copy = copy.deepcopy(g)
    for s in g:
        subgraph = nx.subgraph(g, set(list(nx.descendants(g, s))))
        subgraph = nx.DiGraph(subgraph)
        nodes = [s for s in subgraph]
        sub_results = [results[n] for n in results if n in nodes]
        g.nodes[s]['reducible'] = False
        if len(set(sub_results))<2:
            g.nodes[s]['reducible'] = True
            # sub_results has size 0 or 1: 0 if end node, 1 else
            if results[s]:
                pos_cluster.append(s)
            else:
                neg_cluster.append(s)

    for s in pos_cluster:
        g_copy = nx.contracted_nodes(g_copy, "pos", s)
    for s in neg_cluster:
        g_copy = nx.contracted_nodes(g_copy, "neg", s)
   
    g_copy.remove_edges_from(nx.selfloop_edges(g_copy))

    for s in g_copy.nodes:
        
        pos = False
        neg = False
        if s not in g:
            # after contraction
            continue
        for n in g_copy[s]:
            if "pos" in n:
                pos = True
            if "neg" in n:
                neg = True
        
        if pos and neg and len(g_copy[s]) == 2:
            assert(s in g.nodes)
            g.nodes[s]['decision_boundary'] = True
            #g.nodes[s]['viz'] = {'color': {'r': 0, 'g': 0, 'b':255, 'a': 0}}
            g.nodes[s]['color'] = "blue"
            g.nodes[s]['shape'] = "box"
            g.nodes[s]['viz'] = {'color': {'r': 0, 'g': 0, 'b': 255, 'a': 0}}
        else:
            assert(s in g.nodes)
            g.nodes[s]['decision_boundary'] = False
    
    return g

def game_db(g, results):
    g_copy = copy.deepcopy(g)
    positive_cluster = []
    for s in results:
        if results[s]:
            g_copy.nodes[s]['color'] = "green"
            positive_cluster.append(s)

    # attempted merge:
    negative_cluster = []
    for s in g_copy.nodes:
        reachable = set(list(nx.descendants(g_copy, s)))
        reaches_pos = False
        for neighbour in reachable:
            if "pos" in neighbour:
                reaches_pos = True
        if "pos" in s:
            reaches_pos = True
        if not reaches_pos:
            g_copy.nodes[s]['color'] = "red"
            negative_cluster.append(s)
    for s in negative_cluster:
        g_copy = nx.contracted_nodes(g_copy, "neg", s)
    for s in positive_cluster:
        g_copy = nx.contracted_nodes(g_copy, "pos", s)

    db = []
    for s in g:
        pos = False
        neg = False
        g.nodes[s]['decision_boundary'] = False
        g.nodes[s]['positive_guarantee'] = results[s]
        if s in g_copy:
            for n in g_copy[s]:
                if "pos" in n:
                    pos = True
                if "neg" in n:
                    neg = True
            if pos and neg and len(g_copy[s]) == 2:
                db.append(s)
                g.nodes[s]['decision_boundary'] = True
                g.nodes[s]['color'] = "blue"
                g.nodes[s]['shape'] = "box"
                g.nodes[s]['viz'] = {'color': {'r': 0, 'g': 0, 'b': 255, 'a': 0}}

    return g, db

# Load graph
g = nx.read_gexf(args.input)

# Compute single results
g, results = query(g, args.query)

# Compute decision boundary
if not args.static:
    g, db = game_db(g, results)
else:
    #g, db = db_shortcut(g)
    g = reachable_cluster(g, results)

name = args.output+"DECB"+ args.input.split("/")[-1].split(".")[0].split("GAME")[-1] + "_unrolling_factor:" + str(args.unrolling_factor) + "_" + ".gexf"

nx.write_gexf(g, name)
print("Generated:", name)