
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