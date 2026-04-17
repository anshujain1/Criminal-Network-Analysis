"""Quick local validation using NetworkX -- confirms the synthetic data and
analysis logic actually work BEFORE you set up Neo4j Aura. This is not
part of the final deliverable; it's a debugging aid.
"""

import csv
import networkx as nx
from datetime import datetime


def load_calls(path="data/calls.csv"):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def build_graph(calls):
    G = nx.Graph()
    for c in calls:
        G.add_edge(c["caller_id"], c["callee_id"])
    return G





