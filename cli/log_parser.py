import argparse
import copy
import pandas as pd
import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer

parser = argparse.ArgumentParser(
                    prog = 'log_parser',
                    description = "Takes the BPIC'17 event log as input and performs the preprocessing described in 'Building User Journey Games from Multi-party Event Logs' by Kobialka et al. Outputs two event logs by default: before and after the concept drift in July.",)
parser.add_argument('input', help = "Input file for BIPC'17 event log") 
parser.add_argument('output', help = "Output path for processed event logs") 
parser.add_argument('-mst', '--min_speaking_time', help = "Minimum duration of an aggregated call event to be considered (in sec.); default = 60", default = 60) 
parser.add_argument('-d', '--day_timeout', help = "Number of days until the cancellation is considered a timeout; default = 20", default = 20) 

args = parser.parse_args()

# Filter function to remove outliers; all singleton traces
def filter_log(log):
    perc = 2/len(log)
    return pm4py.filter_variants_by_coverage_percentage(log, perc)

# Contains function on traces, returns true if element is contained
def contains(trace, element):
    for event in trace:
        if event['concept:name']==element:
            return True

def construct_log(log):
    terminal_states = ['A_Cancelled COMPANY', 'A_Cancelled CUSTOMER', 'A_Pending', 'TIMEOUT']
    to_merge = ['W_Call incomplete files', 'W_Call after offers', 'W_Complete application', 'W_Validate application']
    log_activities = []
    for trace in log:
        current_trace = [trace[0]]
        current_trace[0]['case:concept:name'] = trace.attributes['concept:name']
        for i in range(1,len(trace)):
            pos = trace[i]
            pos['case:concept:name'] = trace.attributes['concept:name']
            if "W_Call" in trace[i]['concept:name']:
                # search for closing event
                if pos['lifecycle:transition'] in ["start", "resume"]:
                    for inner_index in range(i+1, len(trace)):
                        inner_pos = trace[inner_index]
                        if pos['concept:name'] == inner_pos['concept:name']:
                            if inner_pos['lifecycle:transition'] in ["suspend", "complete"]:                 
                                duration = (inner_pos['time:timestamp']-pos['time:timestamp']).total_seconds()
                                if duration > args.min_speaking_time:
                                    if pos['concept:name'] in current_trace[-1]["concept:name"]:
                                        current_trace[-1]["duration"] += duration
                                    else:
                                        current_trace.append(pos)
                                        current_trace[-1]['duration'] = duration
                                    if current_trace[-1]["duration"] < 600:
                                        current_trace[-1]['concept:name'] = pos['concept:name']+" SHORT"
                                    elif current_trace[-1]["duration"] < 14400:
                                        current_trace[-1]['concept:name'] = pos['concept:name']+" LONG"
                                    else:
                                        current_trace[-1]['concept:name'] = pos['concept:name']+" SUPER LONG"
                            break
            if "W_" in trace[i]['concept:name']:
                continue # skip other workflow events
            if trace[i]['concept:name'] in ["A_Created", "A_Complete", "A_Incomplete"]:
                continue # skip trivial elements
            if trace[i]['concept:name'] == "A_Cancelled": #differentiate between user_abort and timeout
                current_trace.append(pos)
                if (trace[i]['time:timestamp']-trace[i-1]['time:timestamp']).days >= args.day_timeout:
                    current_trace[-1]['concept:name'] = "TIMEOUT"
                else:
                    current_trace[-1]['concept:name'] += " CUSTOMER"
                continue
            if "O_Created" == trace[i]['concept:name']:
                continue # merge create and created
            if trace[i]['concept:name'] in terminal_states:
                current_trace.append(pos)
            else:
                if trace[i]['concept:name'] in to_merge and trace[i]['concept:name'] == trace[i-1]['concept:name']:
                    continue
                else:
                    current_trace.append(pos)
        if "A_Pending" in [pos['concept:name'] for pos in current_trace]:
            if "O_Cancelled" in [pos['concept:name'] for pos in current_trace]:
                for pos1 in current_trace:
                    if 'O_Cancelled' in pos1['concept:name']:
                        current_trace.remove(pos1)
        intersection = [i for i in trace if i['concept:name'] in terminal_states]
        for state in terminal_states:
            indices = [i for i, x in enumerate(current_trace) if x['concept:name'] == state]
            if indices:
                current_trace = current_trace[:indices[0]+1]
        if intersection:
            log_activities.append(current_trace)
    
    return log_activities

# process log to iterate created offers and differentiate between positive and negative traces
def process_log(log):
    MAX_INDEX = 100
    for trace in log:
        isPositive = False
        if contains(trace, 'A_Pending'):
            isPositive = True
        trace.insert(0,{'concept:name': 'start', 'case:concept:name': trace[0]['case:concept:name'], 'time:timestamp': trace[0]['time:timestamp']})
        if isPositive:
            trace.append({'concept:name': 'positive', 'case:concept:name': trace[0]['case:concept:name'], 'time:timestamp': trace[0]['time:timestamp']})
        else:
            trace.append({'concept:name': 'negative', 'case:concept:name': trace[0]['case:concept:name'], 'time:timestamp': trace[0]['time:timestamp']})
    
    to_extend = ["O_Create Offer"]
    for name in to_extend:
        for trace in log:
            indices = [i for i, x in enumerate(trace) if x['concept:name'] == name]
            for i in indices:
                count_indices = [j for j in indices if j < i]
                index = MAX_INDEX if len(count_indices) > MAX_INDEX else len(count_indices)
                trace[i]['concept:name'] += " "+str(index)


def export(log, path):
    log_df = pd.DataFrame()
    for trace in log:
        log_df = log_df.append(trace, ignore_index=True)

    event_log = pm4py.convert_to_event_log(log_df)
    pm4py.write_xes(event_log, path+".xes")

# Load the log
log = xes_importer.apply(args.input)

# split at concept drift
log_before = pm4py.filter_time_range(log, "2011-03-09 00:00:00", "2016-06-30 23:59:59", mode='traces_contained')
log_after = pm4py.filter_time_range(log, "2016-08-01 00:00:00", "2018-03-09 00:00:00", mode='traces_contained')

# filter outliers
filtered_log_before = filter_log(log_before)
filtered_log_after = filter_log(log_after)

# construct log
filtered_log_before = construct_log(filtered_log_before)
filtered_log_after = construct_log(filtered_log_after)

# append positive or negative outcome
process_log(filtered_log_before)
process_log(filtered_log_after)

#export
export(filtered_log_before, args.output+"bpic2017_before")
export(filtered_log_after, args.output+"bpic2017_after")