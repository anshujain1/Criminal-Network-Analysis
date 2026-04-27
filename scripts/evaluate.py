"""
Ground-truth evaluation of the two "smart" components in this project:
burner-phone detection and link prediction. This exists because a
heuristic or a link-prediction score is only as credible as its measured
accuracy -- "it found the burner in my demo" is an anecdote, not evidence.

Because the dataset is synthetic, we KNOW the ground truth:
  - generate_synthetic_data.py always injects exactly one burner
    (person_id == "P_BURNER_01") -- see scripts/generate_synthetic_data.py
  - We can evaluate link prediction properly via the standard technique:
    hide a random sample of real edges, run prediction on the rest, and
    check how highly the hidden edges are ranked among all predictions.

Run: python scripts/evaluate.py
Outputs: prints metrics to console AND writes evaluation_report.json
"""

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


def evaluate_burner_detection(calls, window_days=5, max_calls=15):
    """
    Precision/recall/F1 against the single known burner.
    Note: with only 1 true positive in the dataset, these numbers are
    illustrative of the METHOD, not a claim of statistical significance --
    that limitation is stated explicitly, not hidden.
    """
    flagged, all_people = burner_candidates(calls, window_days, max_calls)
    true_positive = TRUE_BURNER_ID in flagged
    false_positives = flagged - {TRUE_BURNER_ID}

    precision = 1 / len(flagged) if true_positive and flagged else (0 if flagged else None)
    recall = 1.0 if true_positive else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision and (precision + recall) > 0 else 0.0

    return {
        "true_burner_flagged": true_positive,
        "num_flagged_total": len(flagged),
        "false_positive_ids": sorted(false_positives),
        "precision": round(precision, 3) if precision is not None else None,
        "recall": recall,
        "f1": round(f1, 3),
        "note": "Single known positive in dataset -- treat as a method sanity "
                "check, not a statistically powered evaluation.",
    }


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
    aa_scores = {(u, v): s for u, v, s in nx.adamic_adar_index(G_train, non_edges_train)}

    ranked = sorted(aa_scores.items(), key=lambda x: -x[1])
    ranked_pairs = [frozenset(pair) for pair, _ in ranked]

    hidden_frozen = {frozenset(e) for e in hidden_edges}
    ranks = [ranked_pairs.index(e) for e in hidden_frozen if e in ranked_pairs]

    n = len(ranked_pairs)
    mean_percentile = round(100 * (1 - (sum(ranks) / len(ranks)) / n), 2) if ranks else None

    hit_at_50 = sum(1 for r in ranks if r < 50)
    hit_rate_50 = round(hit_at_50 / len(hidden_edges), 3) if hidden_edges else None

    return {
        "num_edges_hidden": len(hidden_edges),
        "num_candidate_pairs": n,
        "hidden_edges_found_in_ranking": len(ranks),
        "mean_percentile_rank": mean_percentile,
        "hit_rate_at_top_50": hit_rate_50,
        "note": "Higher mean_percentile_rank (closer to 100) means hidden real "
                "edges are ranked near the top of predictions -- i.e. the "
                "method is doing better than random guessing.",
    }


if __name__ == "__main__":
    calls = load_calls()

    logger.info("Evaluating burner-phone detection against known ground truth...")
    burner_results = evaluate_burner_detection(calls)
    logger.info(f"Burner detection results: {burner_results}")

    logger.info("Evaluating link prediction via hidden-edge recovery...")
    link_results = evaluate_link_prediction(calls)
    logger.info(f"Link prediction results: {link_results}")

    report = {
        "burner_detection": burner_results,
        "link_prediction": link_results,
    }

    with open("evaluation_report.json", "w") as f:
        json.dump(report, f, indent=2)

    logger.info("Full report written to evaluation_report.json")
