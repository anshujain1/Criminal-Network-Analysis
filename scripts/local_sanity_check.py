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

def burner_candidates(calls, window_days=5, max_calls=15):
    by_person = {}
    for c in calls:
        for role in ("caller_id", "callee_id"):
            pid = c[role]
            by_person.setdefault(pid, []).append(datetime.fromisoformat(c["timestamp"]))

    candidates = []
    for pid, times in by_person.items():
        times.sort()
        span = (times[-1] - times[0]).days
        if span <= window_days and len(times) <= max_calls:
            candidates.append((pid, len(times), span))
    return sorted(candidates, key=lambda x: x[1])
if __name__ == "__main__":
    calls = load_calls()
    G = build_graph(calls)

    print(f"Graph: {G.number_of_nodes()} people, {G.number_of_edges()} unique connections")

    degree = sorted(G.degree, key=lambda x: -x[1])[:10]
    print("\nTop 10 by degree centrality:")
    for node, d in degree:
        print(f"  {node}: {d} connections")

    betweenness = nx.betweenness_centrality(G)
    top_between = sorted(betweenness.items(), key=lambda x: -x[1])[:10]
    print("\nTop 10 by betweenness centrality (brokers):")
    for node, score in top_between:
        print(f"  {node}: {score:.4f}")

    print("\nBurner phone candidates (short window, low call volume):")
    for pid, num_calls, span in burner_candidates(calls):
        print(f"  {pid}: {num_calls} calls over {span} day(s)")

    communities = nx.community.louvain_communities(G, seed=42)
    print(f"\nDetected {len(communities)} communities via Louvain:")
    for i, c in enumerate(communities):
        print(f"  Community {i}: {sorted(c)[:8]}{'...' if len(c) > 8 else ''} ({len(c)} members)")



print(G.number_of_nodes(), G.number_of_edges())

degree = sorted(G.degree, key=lambda x: -x[1])[:10]
print(degree)

betweenness = nx.betweenness_centrality(G)
top_between = sorted(betweenness.items(), key=lambda x: -x[1])[:10]
print(top_between)

print(burner_candidates(calls))

communities = nx.community.louvain_communities(G, seed=42)
print(len(communities))
for c in communities:
    print(c)