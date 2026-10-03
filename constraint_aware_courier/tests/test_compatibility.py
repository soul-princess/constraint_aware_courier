"""
test_compatibility.py
======================
Failure/edge Case 3: Incompatible products -> batch rejected with explanation.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

from src import constraints


def _order(order_id, category, group=None):
    return pd.Series({
        "order_id": order_id, "product_category": category,
        "incompatible_group": group,
    })


def test_normal_and_fragile_compatible():
    result = constraints.check_pair_compatibility(
        _order("ORD1", "Normal"), _order("ORD2", "Fragile"))
    assert result.passed


def test_frozen_and_hot_food_incompatible():
    result = constraints.check_pair_compatibility(
        _order("ORD1", "Frozen"), _order("ORD2", "Hot Food"))
    assert not result.passed
    assert "Frozen" in result.reason and "Hot Food" in result.reason


def test_fragile_and_heavy_incompatible():
    result = constraints.check_pair_compatibility(
        _order("ORD1", "Fragile"), _order("ORD2", "Heavy"))
    assert not result.passed


def test_chemical_and_normal_incompatible():
    result = constraints.check_pair_compatibility(
        _order("ORD1", "Chemical"), _order("ORD2", "Normal"))
    assert not result.passed


def test_batch_compatibility_checks_all_pairs():
    orders = [_order("ORD1", "Normal"), _order("ORD2", "Fragile"), _order("ORD3", "Heavy")]
    # Fragile + Heavy pair inside a 3-order batch should trigger rejection
    result = constraints.check_batch_compatibility(orders)
    assert not result.passed


def test_group_level_conflict_within_same_category():
    """Two Frozen orders from conflicting sub-groups (e.g. different cold-chain
    vendors) should be rejected even though 'Frozen+Frozen' is broadly allowed."""
    order_a = _order("ORD1", "Frozen", group="FRO-G1")
    order_b = _order("ORD2", "Frozen", group="FRO-G2")
    result = constraints.check_pair_compatibility(order_a, order_b)
    assert not result.passed
    assert "Group-level incompatibility" in result.reason


def test_group_level_same_group_allowed():
    order_a = _order("ORD1", "Frozen", group="FRO-G1")
    order_b = _order("ORD2", "Frozen", group="FRO-G1")
    result = constraints.check_pair_compatibility(order_a, order_b)
    assert result.passed
