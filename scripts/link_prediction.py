"""
link_prediction.py

Predicts likely-but-unrecorded connections between people based on
network structure alone (not on any personal attributes).

Honest scope note: this uses classic, fully explainable graph-theoretic
link prediction methods (Jaccard coefficient and Adamic-Adar index) --
NOT a graph neural network. These are the same class of methods used as
baselines in real link-prediction research and are far easier to defend
in an interview than a GNN you can't fully explain. If you later have
time, this is the natural place to swap in node2vec + a classifier as
a "future work" upgrade.

How to read the output: a high score between two people who have NEVER
directly called each other means they share many common contacts --
i.e. they likely know each other through the network even without a
recorded direct link. This is a real technique used in investigative
link analysis to surface "probable but unconfirmed" connections.

Run: python scripts/link_prediction.py
"""

import csv
import networkx as nx


def load_graph(path="data/calls.csv"):
    G = nx.Graph()
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            G.add_edge(row["caller_id"], row["callee_id"])
    return G


def predict_links(G, top_n=15):
    # Only consider pairs that are NOT already directly connected
    non_edges = list(nx.non_edges(G))

    jaccard_scores = list(nx.jaccard_coefficient(G, non_edges))
    adamic_adar_scores = list(nx.adamic_adar_index(G, non_edges))

    jaccard_ranked = sorted(jaccard_scores, key=lambda x: -x[2])[:top_n]
    aa_ranked = sorted(adamic_adar_scores, key=lambda x: -x[2])[:top_n]

    return jaccard_ranked, aa_ranked


if __name__ == "__main__":
    G = load_graph()
    print(f"Loaded graph: {G.number_of_nodes()} people, {G.number_of_edges()} recorded connections")

    jaccard_ranked, aa_ranked = predict_links(G)

    print("\n=== Top predicted (unrecorded) links -- Jaccard Coefficient ===")
    print("(fraction of shared contacts out of all contacts either person has)")
    for u, v, score in jaccard_ranked:
        if score > 0:
            print(f"  {u} <-> {v}: {score:.3f}")

    print("\n=== Top predicted (unrecorded) links -- Adamic-Adar Index ===")
    print("(weights rare shared contacts more heavily than common ones)")
    for u, v, score in aa_ranked:
        if score > 0:
            print(f"  {u} <-> {v}: {score:.3f}")

    print("\nInterpretation: pairs with high scores share several common "
          "contacts despite never calling each other directly -- worth "
          "flagging for manual review as a probable, unconfirmed link.")
