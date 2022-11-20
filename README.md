# Building User Journey Games from Multi-party Event Logs
This is the repository for the paper "Building User Journey Games from Multi-party Event Logs'' by Kobialka, Mannhardt, Tapia Tarifa and Johnsen.
The paper introduces a multi-party view on event logs and promotes a game theoretic model for user journey models.
It introduces the concept of a "decision boundary", a subset of nodes after which the outcome of the user journey is determined.
The outcome of the journey can not be changed after leaving the decision boundary.
The decision boundary is used for a model reduction preserving the decision structure of the game, allowing to apply the method to real-world event logs.
- The evaluation is implemented in "main.ipynb". The notebook produces all plots.
- The folder simulations contains "max.csv", "step.csv" and "both.csv"; the data from the respective UPPAAL simulations, Fig. 4. The simulations are produced with the queries in "queries.q".
- "clustered_before.png" and "clustered_after.png" contain the process models, Fig 4.
- "activities.xml" contains the actors for events (user or company).

# Model Checking
To model check the queries was UPPAAL 4.1.20 with Stratego 9 for Linux-64 used.

Note: the construction of plots creates additional *.dot files.

# Command line tool
The folder 'cli' contains the command line tool to compute the decision boundary of a XES event-log, consisting of several independent programs.
All tools are implemented as command-line tools in Python.
The file 'execution.py' demonstrates how the tools are connected and implements parameter tests for ranges of transition system histories and unrolling factors.
Mind that for every step a single file is created, the output might be excessive.

Each program takes the result of the prior step as input and produces the next part of the pipeline described in the paper "Building User Journey Games from Multi-party Event Logs'' by Kobialka etal.
Each tool saves the chosen parameters in the filename of the written output and prints the output filename to the console.
 
Transition systems and games are saved in the ".gexf" fileformat, [.gexf](https://gexf.net/).
Further details on written parameters are in the subsection "File Format".

- "log_parser.py'' takes the BPIC'17 event log as input and performs the described preprocessing, writing two separate event-logs as output, called "bpic2017_after.xes" and "bpic2017_before.xes".
- "process_model.py'' constructs a process model from a preprocessed event log. The user can decide to either choose the "sequence" abstraction or the "multiset" abstraction and the length of the history. The resulting process model is 
- "build_game.py'' transform the process model to a game by annotating the edges with actor information.
The actor information is given as input in JSON. Every not given edge is considered to be controllable.
- "decision_boundary.py'' computes the decision boundary and writes the annotated game as output, the reduction is only performed in the next step.
- "decision_boundary_reduction.py'' applies the decision boundary reduction: Merging all negative nodes into one and all positive nodes.

## File format
We use the ".gexf" file format to store transition systems, and games.

Edges contain the fields:
- "action" the activity performed along causing the edge
- "controllable" (bool) indicating if the edge is controllable (company controlled) or user controlled.
- "cost" stating the weight of the edge
- "edge_traversal" the number of traversals along the edge

Nodes contain the fields:
- "node_traversal" sums up "edge_traversal" over outgoing edges
- "positive_guarantee" indicating if the node guarantees a positive outcome
- "decision_boundary" indicating the containment in the decision boundary
- "final" is only a field set to true 
