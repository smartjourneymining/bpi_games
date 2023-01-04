import argparse
import pandas as pd
import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer
import copy
from collections import Counter
from sklearn import mixture
import numpy as np 

parser = argparse.ArgumentParser(
                    prog = 'log_parser',
                    description = "Takes the BPIC'12 event log as input and performs the preprocessing described in 'Building User Journey Games from Multi-party Event Logs' by Kobialka et al, the processed event log is written as output",)
parser.add_argument('input', help = "Input file for BIPC'12 event log") 
parser.add_argument('output', help = "Output path for processed event log") 
parser.add_argument('-mst', '--min_speaking_time', help = "Minimum duration of an aggregated call event to be considered (in sec.); default = 60", default = 60) 
parser.add_argument('-d', '--day_timeout', help = "Number of days until the cancellation is considered a timeout; default = 20", default = 20) 
parser.add_argument('-c', '--cluster_components', help = "Number of maximal clusters allowed used for call durations; default = 3", default = 3, type = int) 

args = parser.parse_args()

# helpfer function to check if element is contained in trace
def contains(trace, element):
    for event in trace:
        if event['concept:name']==element:
            return True
    return False

# investigate number of offers - has no event for "sent offer"
# discretise single 0_CREATED and 0_SENT events
# works in_place (modified the passed log)
def count_offers(log):
    for trace in log:
        offer_count = -1
        for e in trace:
            if "O_CREATED" in e["concept:name"]:
                offer_count += 1
                e["concept:name"] += str(offer_count)

            elif "O_SENT" in e["concept:name"] and "BACK" not in e["concept:name"]:
                e["concept:name"] += str(offer_count)

# Transform log into list format, log is represented as list of lists, easier removal and insertion of single events.
def log_to_list(log):
    transformed_log = []
    for trace in log:
        current_trace = []
        for event in trace:
            event['case:concept:name'] = trace.attributes['concept:name']
            current_trace.append(event)
        current_trace.insert(0, {"concept:name": "start", 'case:concept:name':trace.attributes['concept:name'], 'time:timestamp': trace[0]['time:timestamp']}) #insert start event
        transformed_log.append(current_trace)
    return transformed_log


# Only cancelled and approved events are kept in the log, Final events are appended.
def filter_incomplete_traces(log):
    transformed_log = []
    outcomes = ["A_CANCELLED", "A_APPROVED"] # "A_DECLINED",
    for trace in log:
        trace_copy = copy.deepcopy(trace)
        contained = False
        for o in outcomes:
            if contains(trace, o):
                contained = True
        if contained:
            if contains(trace, "A_CANCELLED"):
                trace_copy.append({'concept:name': "negative", 'time:timestamp': trace[-1]['time:timestamp'], 'case:concept:name': trace[0]['case:concept:name']})
            if contains(trace, "A_APPROVED"):
                trace_copy.append({'concept:name': "positive", 'time:timestamp': trace[-1]['time:timestamp'], 'case:concept:name': trace[0]['case:concept:name']})
            assert(contains(trace_copy, "negative") or contains(trace_copy, "positive"))
            transformed_log.append(trace_copy)
    return transformed_log

def variants(log):
    element_list = []
    for trace in log:
        new_trace = [k["concept:name"] for k in trace]
        element_list.append(new_trace)
    print(len(Counter(str(e) for e in element_list).keys()))

# Filter events from log and compute durations of single calls
def adjust_durations(log):
    transformed_log = []
    for trace in log:
        new_trace  = []
        for i in range(len(trace)):
            if "W_Nabellen" in trace[i]['concept:name']: # omits SCHEDULE and COMPLETE call events
                if trace[i]['lifecycle:transition']=="START":
                    found = False
                    duration = 0
                    j = i
                    while not found:
                        j = j+1
                        if j >= len(trace):
                            for e in trace:
                                print(e["concept:name"], e['lifecycle:transition'])
                        assert(j < len(trace))
                        if trace[j]['concept:name'] == trace[i]['concept:name']:
                            assert(trace[j]['lifecycle:transition'] != "START")
                            if  trace[j]['lifecycle:transition']=="COMPLETE":
                                found = True
                                duration = (trace[j]['time:timestamp']-trace[i]['time:timestamp']).total_seconds()
                        
                    if duration > args.min_speaking_time:
                        if new_trace[-1]["concept:name"] == trace[i]['concept:name']: # merge call times together
                            new_trace[-1]["duration"] += duration
                        else:
                            new_element = copy.deepcopy(trace[i])
                            new_element["duration"] = duration
                            new_trace.append(new_element)
            if trace[i]['concept:name'] == "A_Cancelled": #differentiate between user_abort and timeout
                new_element = copy.deepcopy(trace[i])
                if (trace[i]['time:timestamp']-trace[i-1]['time:timestamp']).days >= args.day_timeout or (trace[i]['time:timestamp']-trace[i-2]['time:timestamp']).days >= args.day_timeout :
                    new_element[-1]['concept:name'] = "TIMEOUT"
                    assert(False) # no timeouts detected before cancellation
                else:
                    new_element[-1]['concept:name'] += " CUSTOMER"
                new_trace.append(new_element)
            else:
                if "W_" in trace[i]['concept:name']:  # skip other workflow elements
                    continue
                if "O_SELECTED" in trace[i]['concept:name']:
                    continue
                if "O_SENT" in trace[i]['concept:name'] and "BACK" not in trace[i]['concept:name']: # skip sent event, but not send_back
                    continue
                elif "O_DECLINED" in trace[i]['concept:name'] or "A_PARTLYSUBMITTED" in trace[i]['concept:name']: # skip trivial elements
                    continue
                else:
                    new_trace.append(trace[i])

        transformed_log.append(new_trace)
    return transformed_log

# Function to merge the 4 events present in successful logs: A_APPROVED, O_ACCEPTED, A_ACTIVATED and A_REGISTERED
def merge_successful(log):
    transformed_log = []
    for trace in log:
        if contains(trace, "A_APPROVED"):
            modified_trace = copy.deepcopy(trace)

            for j in range(len(modified_trace)):
                if modified_trace[j]["concept:name"] == "O_ACCEPTED":
                    modified_trace.pop(j)
                    break

            for j in range(len(modified_trace)):
                if modified_trace[j]["concept:name"] == "A_ACTIVATED":
                    modified_trace.pop(j)
                    break
            
            for j in range(len(modified_trace)):
                if modified_trace[j]["concept:name"] == "A_REGISTERED":
                    modified_trace.pop(j)
                    break
            
            transformed_log.append(modified_trace)

        else:
            transformed_log.append(trace)
    return transformed_log

# Cluster call events based on call durations by Bayesian-Gaussian mixture clustering
def get_bayesian_gaussian_mixture(components, times):
    duration_classifier = {}
    for t in times:
        if len(times[t])==1:
            g = mixture.BayesianGaussianMixture(n_components=1,covariance_type='full')
            g.fit(np.array([[times[t]], [times[t]]]).reshape(-1, 1))
            duration_classifier[t] = g
            continue
        
        g = mixture.BayesianGaussianMixture(n_components=components,covariance_type='full', random_state=42)
        g.fit(np.array(times[t]).reshape(-1,1))
        duration_classifier[t] = g
    return duration_classifier

def classify_log(log, predictor):
    log = copy.deepcopy(log)
    for trace in log:
        for pos in range(1,len(trace)):
            action = trace[pos]["concept:name"]
            if "W_Nabellen" not in action:
                continue
            assert("duration" in trace[pos])
            duration = trace[pos]["duration"]
            suffix = str(predictor[action].predict(np.array(duration).reshape(1,-1))[0])
            assert(int(suffix) in list(range(0,100)))
            trace[pos]["concept:name"] += "#"+suffix

    return log

# export the log for easier further analysis
def export(log, path):
    # to use the pm4py write_xes function, an pm4py event log object is needed.
    # for this is the list event log via the pandas data frame to a pm4py event log converted.
    log_df = pd.DataFrame()
    for trace in log:
        assert(trace[0]["concept:name"]=="start")
        assert(contains(trace, "negative") or contains(trace, "positive"))
        log_df = log_df.append(trace, ignore_index=True)

    event_log = pm4py.convert_to_event_log(log_df)
    pm4py.write_xes(event_log, path) 

#load event log
log_application = xes_importer.apply(args.input)

# enumerate offers
count_offers(log_application)
# transform to list
list_log_application = log_to_list(log_application)
#remove incomplete traces
list_log_application = filter_incomplete_traces(list_log_application)
print("Variants before removing trivial elements")
variants(list_log_application)
#remove trivial elements
list_log_application = adjust_durations(list_log_application)
list_log_application = merge_successful(list_log_application)
print("Variants after removing trivial events")
variants(list_log_application)

# uses Bayesian-Gaussian Mixture clustering to discretise durations
response_times = {}
for trace in list_log_application:
    for e in trace:
        if "W_Nabellen" in e['concept:name']:
            if e['concept:name'] not in response_times:
                response_times[e['concept:name']] = []
            response_times[e['concept:name']].append(e['duration'])

predictor = get_bayesian_gaussian_mixture(args.cluster_components, response_times)
list_log_application = classify_log(list_log_application, predictor)

# write output
export(list_log_application, args.output+"bpi2012.xes")