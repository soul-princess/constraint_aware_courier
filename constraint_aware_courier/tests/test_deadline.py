"""
test_deadline.py
=================
Failure/edge Case 2: Promised deadline cannot be met -> batch must be rejected.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta

import pandas as pd

from src import constraints


def _order(deadline_offset_min):
    now = datetime(2025, 1, 6, 9, 0, 0)
    return pd.Series({
        "order_id": "ORD1",
        "promised_deadline": now + timedelta(minutes=deadline_offset_min),
    })


def test_delivery_before_deadline_passes():
    order = _order(60)  # deadline is 60 min from "now"
    predicted_time = datetime(2025, 1, 6, 9, 30, 0)  # delivered in 30 min
    result = constraints.check_deadline_feasibility(order, predicted_time, safety_buffer_min=5)
    assert result.passed


def test_delivery_after_deadline_rejected():
    order = _order(20)  # deadline is 20 min from "now"
    predicted_time = datetime(2025, 1, 6, 9, 40, 0)  # delivered in 40 min -> too late
    result = constraints.check_deadline_feasibility(order, predicted_time, safety_buffer_min=5)
    assert not result.passed
    assert "Deadline violation" in result.reason


def test_delivery_within_safety_buffer_rejected():
    """Even if nominally before the deadline, breaching the safety buffer
    should be treated as infeasible (protects against last-minute delays)."""
    order = _order(30)
    predicted_time = datetime(2025, 1, 6, 9, 27, 0)  # only 3 min buffer, need 5
    result = constraints.check_deadline_feasibility(order, predicted_time, safety_buffer_min=5)
    assert not result.passed
