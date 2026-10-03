"""
test_capacity.py
=================
Failure/edge Case 1: Rider capacity exceeded -> batch must be rejected.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import pytest

from src import constraints


def _order(order_id, weight, volume):
    return pd.Series({
        "order_id": order_id, "weight_kg": weight, "volume_litre": volume,
        "product_category": "Normal", "incompatible_group": None,
        "location_id": "LOC0001", "fragile": False,
    })


def _rider(capacity_kg=20, capacity_volume=50, max_orders=6):
    return pd.Series({
        "rider_id": "RID001", "capacity_kg": capacity_kg,
        "capacity_volume": capacity_volume, "max_orders_per_batch": max_orders,
    })


def test_capacity_within_limits_passes():
    orders = [_order("ORD1", 5, 10), _order("ORD2", 5, 10)]
    result = constraints.check_capacity(orders, _rider(capacity_kg=20, capacity_volume=50))
    assert result.passed


def test_capacity_weight_exceeded_rejected():
    orders = [_order("ORD1", 15, 10), _order("ORD2", 15, 10)]  # 30kg > 20kg cap
    result = constraints.check_capacity(orders, _rider(capacity_kg=20, capacity_volume=50))
    assert not result.passed
    assert "Capacity exceeded" in result.reason
    assert "weight" in result.reason


def test_capacity_volume_exceeded_rejected():
    orders = [_order("ORD1", 2, 30), _order("ORD2", 2, 30)]  # 60L > 50L cap
    result = constraints.check_capacity(orders, _rider(capacity_kg=20, capacity_volume=50))
    assert not result.passed
    assert "volume" in result.reason


def test_max_orders_per_batch_exceeded_rejected():
    orders = [_order(f"ORD{i}", 1, 1) for i in range(5)]  # 5 orders > max 3
    result = constraints.check_capacity(orders, _rider(max_orders=3))
    assert not result.passed
    assert "Order count exceeded" in result.reason
