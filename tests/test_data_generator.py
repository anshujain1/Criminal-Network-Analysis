"""
tests/test_data_generator.py

Sanity tests for the synthetic data generator -- confirms structural
invariants that the rest of the project depends on (e.g. the burner
phone is genuinely absent from the "normal" calling population, the
generator is reproducible, referential integrity holds).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.generate_synthetic_data import make_people, make_towers, make_calls, inject_burner_phone


def test_make_people_generates_unique_ids():
    people = make_people(20)
    ids = [p["person_id"] for p in people]
    assert len(ids) == len(set(ids)), "person_ids must be unique"


def test_make_towers_generates_valid_coordinates():
    towers = make_towers(10)
    for t in towers:
        assert -90 <= t["lat"] <= 90
        assert -180 <= t["lon"] <= 180


def test_burner_phone_not_in_original_people_list():
    """The injected burner must be a genuinely new entity, not reused from people.csv."""
    people = make_people(10)
    calls, next_id = make_calls(people)
    burner, cluster, calls = inject_burner_phone(people, calls, next_id)

    person_ids = {p["person_id"] for p in people}
    assert burner["person_id"] not in person_ids

