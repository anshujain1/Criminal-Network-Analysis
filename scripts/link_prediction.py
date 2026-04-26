import csv
import networkx as nx


def load_graph(path="data/calls.csv"):
    G = nx.Graph()

    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            G.add_edge(
                row["caller_id"],
                row["callee_id"]
            )

    return G

def predict_links(G, top_n=15):
    # Only consider pairs that are not already connected
    non_edges = list(nx.non_edges(G))

    jaccard_scores = list(
        nx.jaccard_coefficient(G, non_edges)
    )

    adamic_adar_scores = list(
        nx.adamic_adar_index(G, non_edges)
    )

    jaccard_ranked = sorted(
        jaccard_scores,
        key=lambda x: -x[2]
    )[:top_n]

    aa_ranked = sorted(
        adamic_adar_scores,
        key=lambda x: -x[2]
    )[:top_n]

    return jaccard_ranked, aa_ranked

if __name__ == "__main__":
    G = load_graph()

    print(
        f"Loaded graph: {G.number_of_nodes()} people, "
        f"{G.number_of_edges()} recorded connections"
    )