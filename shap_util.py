from sklearn import tree
from sklearn.tree import export_graphviz
import pydotplus
import shap
import matplotlib.pyplot as plt
import numpy as np 
import json 
import pandas as pd 
import copy
import networkx as nx 

def ms(trace):
    multiset = {}
    for pos in trace:
        if pos['concept:name'] not in multiset:
            multiset[pos['concept:name']] = 1
        else:
            multiset[pos['concept:name']] += 1
    return json.dumps(multiset, sort_keys=True).encode().decode("utf-8") # use json encodings for multisets

def hist(trace): 
    hist = str(trace[0]['concept:name'])
    for pos in trace[1:]:
        hist += " - " + str(pos['concept:name']) # construct history
    return hist

def to_df_one_hot_inner(log, system, limit, abstraction, hist_length):
    system = copy.deepcopy(system)
    system = nx.relabel_nodes(system, {'pos':'positive', 'neg':'negative'})
    
    log_acitivities = set()
    for trace in log:
        log_acitivities.update(set([t['concept:name'] for t in trace]))
    #log_acitivities.add("y")
    trace_df = pd.DataFrame(columns = list(log_acitivities))
    data_list = []
    for trace in log:
        trace_edges = [x['concept:name'] for x in trace]
        data = {}
        assert(trace[0]['concept:name']=="start")
        for i in range(max(1,len(trace)-limit)): #range(1,len(trace_edges)):
            t = abstraction(trace[max(0,i-hist_length+1):i+1])
            current = trace_edges[i]
            if t not in list(system.nodes()):
                continue
            if current not in data:
                data[current] = 1
            # one hot encoding - no additional counting
        data_list.append(data)
    trace_df = pd.DataFrame(data_list)
    # trace_df = pd.concat([trace_df, pd.DataFrame(data, index = [0])], ignore_index=True)
    trace_df = trace_df.fillna(0)
    assert(len(trace_df.index) == len(log))
    return trace_df

def beeswarm_comparison(removed_columns, log, system, abstraction, hist_length, name='tree', limit_start=0, limit_end=25+1, sample=200, plot=False):
    Y = [(1 if 'positive' in [e['concept:name'] for e in t] else 0) for t in log] # construct Y values from log    

    for limit in range(limit_start, limit_end+1):
        df_one_hot = to_df_one_hot_inner(log, system, limit, abstraction, hist_length)
        X = df_one_hot
        assert len(X) == len(Y), f'{len(X)} does not match {len(Y)}'
        if 'positive' in X.columns:
            X = df_one_hot.drop(['positive'], axis=1)
        if 'negative' in X.columns:
            X = df_one_hot.drop(['negative'], axis=1)
                    
        clf = tree.DecisionTreeClassifier()
        clf = clf.fit(X, Y)

        sub_data = shap.sample(X, sample)
        # sub_data.rename(columns={r : r+' (REMOVED)' if r in removed_columns else r for r in list(sub_data.columns)}, inplace=True)
        explainer = shap.KernelExplainer(clf.predict_proba, data=sub_data, feature_names=['t'])# KernelExplainer
        # shap_values = explainer.shap_values(sub_data)
        shap_obj = explainer(sub_data)[:,:,0]
        ax = shap.plots.beeswarm(shap_obj, show=False, max_display=4, group_remaining_features=True, color_bar=True,)
        # labels = ax.get_yticklabels()
        # ax.set_yticklabels(labels)
        # print(ax.get_yticklabels()[0].s)
        for i in range(len(ax.get_yticklabels())):
            if ax.get_yticklabels()[i].get_text() in removed_columns:
                ax.get_yticklabels()[i].set_color('red')
                ax.get_yticklabels()[i].set_fontweight('bold')
                
                # print("before", ax.get_yticklabels()[i].get_text())
                # p = ax.get_yticklabels()[i]
                # p.set_text('test')
                # print("updated", p.get_text())
                # ax.get_yticklabels()[i].update({'text':'test'})
            
        plt.savefig(f'out/beeswarm/beeswarm_{name}_{limit}')
        print("Limit", limit)
        if plot:
            plt.show()
        else:
            plt.clf()
        
def print_accuracy(pred, Y):
    print(f"Accuracy = {100 * np.sum(pred == Y) / len(Y)}%")
    
def compare_trees(log, system, abstraction, hist_length, removed_columns, limit_start=0, limit_end=25+1):
    Y = [(1 if 'positive' in [e['concept:name'] for e in t] else 0) for t in log] # construct Y values from log    

    result_string = ""
    for limit in range(limit_start, limit_end+1):
        df_one_hot = to_df_one_hot_inner(log, system, limit, abstraction, hist_length)
        # df_one_hot_reduced = to_df_one_hot(filtered_log_before, before_reachable)
        
        print('##############', limit, '#####################')
        
        # Y = df_one_hot['positive']
        X = df_one_hot
        assert len(X) == len(Y), f'{len(X)} does not match {len(Y)}'
        if 'positive' in X.columns:
            X = df_one_hot.drop(['positive'], axis=1)
        if 'negative' in X.columns:
            X = df_one_hot.drop(['negative'], axis=1)
        
        clf = tree.DecisionTreeClassifier()
        clf = clf.fit(X, Y)
        
        
        X_columns = X.columns
        # [e if e not in removed_columns else 'REMOVED' for e in X.columns]
        
        n_nodes = clf.tree_.node_count
        feature = clf.tree_.feature
        children_left = clf.tree_.children_left
        children_right = clf.tree_.children_right
        split_counter = 0
        removed_counter = 0
        for i in range(n_nodes):
            if children_left[i] != children_right[i]: # ensure is split node
                split_counter += 1
                if X_columns[feature[i]] in removed_columns:
                    removed_counter += 1
                    print(f'Used {X_columns[feature[i]]}')
        print(f'used {removed_counter}/{split_counter} removed features')
        print_accuracy(clf.predict(X), Y)
        
        result_string += (str(np.round(100 * np.sum(clf.predict(X) == Y) / len(Y), 2)) + ("" if limit == limit_end  else " & "))
        
        # tree.plot_tree(clf, feature_names=X_columns)
        
        dot_data = export_graphviz(clf,
                            feature_names=X_columns,
                            out_file=f'out/trees/tree_after_{limit}.dot',
                            filled=True,
                            rounded=True,
                            impurity=False)
        # to convert to png: dot -Tpng tree.dot -o tree.png 
        
        # pydot_graph = pydotplus.graph_from_dot_data(dot_data)
        # print(pydot_graph)
        # print(help(pydot_graph))
        # pydot_graph.write_pdf(f'out/trees/tree_after_{limit}.pdf')
        
        plt.show()
    print(result_string)