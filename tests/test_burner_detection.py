"""
tests/test_burner_detection.py

Unit tests for the burner-phone detection heuristic, isolated from any
file I/O or database -- pure logic tests with hand-built edge cases.
This is the kind of test that catches "works on my synthetic data but
breaks on a slightly different pattern" bugs before they matter.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluate import burner_candidates


def make_call(caller, callee, days_offset, call_id):
    ts = (datetime(2026, 1, 1) + timedelta(days=days_offset)).isoformat()
    return {"call_id": f"C{call_id}", "caller_id": caller, "callee_id": callee, "timestamp": ts}


def test_flags_short_burst_low_volume():
    """A number active for 2 days with 3 calls should be flagged."""
    calls = [
        make_call("BURNER", "A", 0, 1),
        make_call("BURNER", "B", 1, 2),
        make_call("BURNER", "C", 2, 3),
    ]
    flagged, _ = burner_candidates(calls, window_days=5, max_calls=15)
    assert "BURNER" in flagged


def test_does_not_flag_long_running_number():
    """A number active across 30 days shouldn't be flagged, even with few calls."""
    calls = [
        make_call("REGULAR", "A", 0, 1),
        make_call("REGULAR", "B", 30, 2),
    ]
    flagged, _ = burner_candidates(calls, window_days=5, max_calls=15)
    assert "REGULAR" not in flagged


def test_does_not_flag_high_volume_number():
    """A number with many calls, even in a short window, exceeds the volume threshold."""
    calls = [make_call("HEAVY_USER", f"P{i}", 0, i) for i in range(20)]
    flagged, _ = burner_candidates(calls, window_days=5, max_calls=15)
    assert "HEAVY_USER" not in flagged


def test_single_call_person_is_flagged():
    """
    Edge case: someone with exactly ONE call ever has a zero-day window
    and trivially low volume -- this WILL be flagged. This is a known,
    intentional limitation: the heuristic can't distinguish 'burner
    phone' from 'person who happens to have very sparse call records
    in this dataset window' with only one data point. Worth stating
    explicitly rather than discovering it live in an interview.
    """
    calls = [make_call("SPARSE", "A", 0, 1)]
    flagged, _ = burner_candidates(calls, window_days=5, max_calls=15)
    assert "SPARSE" in flagged


def test_empty_call_list():
    flagged, all_people = burner_candidates([], window_days=5, max_calls=15)
    assert flagged == set()
    assert all_people == set()


def test_threshold_boundary_exact_window():
    """Exactly at the window_days boundary should still be flagged (<=, not <)."""
    calls = [
        make_call("EDGE", "A", 0, 1),
        make_call("EDGE", "B", 5, 2),  # exactly 5 days apart
    ]
    flagged, _ = burner_candidates(calls, window_days=5, max_calls=15)
    assert "EDGE" in flagged
