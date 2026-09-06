"""
test_readiness.py
==================
Failure/edge Case 4: Pickup order is not ready -> order must not be forced
into the batch (rider should not be made to wait excessively).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta

import pandas as pd

from src import constraints


def _order(ready_offset_min):
    now = datetime(2025, 1, 6, 9, 0, 0)
    return pd.Series({
        "order_id": "ORD1",
        "pickup_ready_time": now + timedelta(minutes=ready_offset_min),
    })


def test_order_ready_before_batch_start_passes():
    batch_start = datetime(2025, 1, 6, 9, 10, 0)
    order = _order(0)  # ready at 9:00, batch starts 9:10 -> no wait needed
    result = constraints.check_pickup_readiness([order], batch_start, max_wait_min=15)
    assert result.passed


def test_order_ready_within_wait_tolerance_passes():
    batch_start = datetime(2025, 1, 6, 9, 0, 0)
    order = _order(10)  # ready 10 min after batch starts, within 15 min tolerance
    result = constraints.check_pickup_readiness([order], batch_start, max_wait_min=15)
    assert result.passed


def test_order_not_ready_exceeds_wait_tolerance_rejected():
    batch_start = datetime(2025, 1, 6, 9, 0, 0)
    order = _order(45)  # ready 45 min after batch starts -> exceeds 15 min tolerance
    result = constraints.check_pickup_readiness([order], batch_start, max_wait_min=15)
    assert not result.passed
    assert "Pickup readiness violation" in result.reason


def test_multiple_orders_one_not_ready_rejects_whole_batch():
    batch_start = datetime(2025, 1, 6, 9, 0, 0)
    ready_order = _order(0)
    ready_order["order_id"] = "ORD_READY"
    not_ready_order = _order(60)
    not_ready_order["order_id"] = "ORD_NOT_READY"
    result = constraints.check_pickup_readiness(
        [ready_order, not_ready_order], batch_start, max_wait_min=15)
    assert not result.passed
    assert "ORD_NOT_READY" in result.reason
