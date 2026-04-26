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

if __name__ == "__main__":
    G = load_graph()

    print(
        f"Loaded graph: {G.number_of_nodes()} people, "
        f"{G.number_of_edges()} recorded connections"
    )