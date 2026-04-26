
import csv
import json
import random
import logging
from datetime import datetime

import networkx as nx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("evaluate")

TRUE_BURNER_ID = "P_BURNER_01"  # ground truth, set by generate_synthetic_data.py


def load_calls(path="data/calls.csv"):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def burner_candidates(calls, window_days=5, max_calls=15):
    by_person = {}
    for c in calls:
        for role in ("caller_id", "callee_id"):
            pid = c[role]
            by_person.setdefault(pid, []).append(datetime.fromisoformat(c["timestamp"]))
    flagged = set()
    for pid, times in by_person.items():
        times.sort()
        span = (times[-1] - times[0]).days
        if span <= window_days and len(times) <= max_calls:
            flagged.add(pid)
    return flagged, set(by_person.keys())

def evaluate_link_prediction(calls, hide_fraction=0.15, seed=42):
    """
    Standard link-prediction evaluation:
      1. Build the full graph.
      2. Randomly hide a fraction of real edges.
      3. Run Jaccard/Adamic-Adar prediction on the REMAINING graph.
      4. Check: how highly are the hidden (real, but removed) edges ranked
         among all non-edges? Report mean percentile rank and hit-rate@k.
    A good method should rank hidden real edges much higher than random.
    """
    random.seed(seed)

    G_full = nx.Graph()
    for c in calls:
        G_full.add_edge(c["caller_id"], c["callee_id"])

    all_edges = list(G_full.edges())
    num_hide = max(1, int(len(all_edges) * hide_fraction))
    hidden_edges = set(random.sample(all_edges, num_hide))

    G_train = G_full.copy()
    G_train.remove_edges_from(hidden_edges)

    non_edges_train = list(nx.non_edges(G_train))

    aa_scores = {
        (u, v): s
        for u, v, s in nx.adamic_adar_index(
            G_train, non_edges_train
        )
    }

    ranked = sorted(
        aa_scores.items(),
        key=lambda x: -x[1]
    )

    ranked_pairs = [
        frozenset(pair)
        for pair, _ in ranked
    ]

    hidden_frozen = {
        frozenset(e)
        for e in hidden_edges
    }

    ranks = [
        ranked_pairs.index(e)
        for e in hidden_frozen
        if e in ranked_pairs
    ]

    n = len(ranked_pairs)

    mean_percentile = (
        round(
            100 * (1 - (sum(ranks) / len(ranks)) / n),
            2
        )
        if ranks else None
    )

    hit_at_50 = sum(1 for r in ranks if r < 50)

    hit_rate_50 = (
        round(hit_at_50 / len(hidden_edges), 3)
        if hidden_edges else None
    )

    return {
        "num_edges_hidden": len(hidden_edges),
        "num_candidate_pairs": n,
        "hidden_edges_found_in_ranking": len(ranks),
        "mean_percentile_rank": mean_percentile,
        "hit_rate_at_top_50": hit_rate_50,
        "note": (
            "Higher mean_percentile_rank (closer to 100) means hidden "
            "real edges are ranked near the top of predictions -- i.e. "
            "the method is doing better than random guessing."
        ),
    }