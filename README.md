# Building User Journey Games from Multi-party Event Logs
This is the repository for the paper "Building User Journey Games from Multi-party Event Logs'' by Kobialka, Mannhardt, Tapia Tarifa and Johnsen.
The paper introduces a multi-party view on event logs and promotes a game theoretic model for user journey models.
It introduces the concept of a "decision boundary", a subset of nodes after which the outcome of the user journey is determined.
The outcome of the journey can not be changed after leaving the decision boundary.
The decision boundary is used for a model reduction preserving the decision structure of the game, allowing to apply the method to real-world event logs.
- The evaluation is implemented in "bpi_main.ipynb". The notebook produces all plots 
- "max.csv", "step.csv" and "both.csv" contain the data from the respective UPPAAL simulations, Fig. 4.
- "clustered_before.png" and "clustered_after.png" contain the process models, Fig 5.

# Model Checking
To model check the queries was UPPAAL 4.1.20 with Stratego 9 for Linux-64 used.
