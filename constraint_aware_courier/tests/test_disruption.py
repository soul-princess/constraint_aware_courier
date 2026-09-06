"""
test_disruption.py
===================
Failure/edge Case 5: Rider becomes unavailable -> orders are automatically
reconsidered/reassigned rather than silently dropped.

Also covers the three disruption scenario generators (rider capacity loss,
travel delay, urgent demand surge) at a unit level, and an integration-style
check that CABA still produces a valid (non-crashing, constraint-respecting)
result when some riders are marked UNAVAILABLE mid-fleet.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

from src import data_generator, disruption, batching_algorithm, constraints
import config


def test_rider_capacity_loss_marks_fraction_unavailable():
    riders = data_generator.generate_riders(n_riders=40, seed=1)
    disrupted = disruption.scenario_rider_capacity_loss(riders, fraction=0.25, seed=1)
    n_unavailable = (disrupted["availability"] == "UNAVAILABLE").sum()
    assert n_unavailable == max(1, int(40 * 0.25))
    # riders not touched should remain AVAILABLE
    assert (disrupted["availability"] == "AVAILABLE").sum() == 40 - n_unavailable


def test_travel_delay_scenario_returns_multiplier_greater_than_one():
    multiplier = disruption.scenario_travel_delay(1.75)
    assert multiplier == 1.75
    assert multiplier > 1.0


def test_urgent_surge_increases_urgent_count():
    orders = data_generator.generate_orders(n_orders=200, seed=2)
    n_urgent_before = (orders["priority"] == "URGENT").sum()
    surged = disruption.scenario_urgent_demand_surge(orders, fraction=0.15, seed=2)
    n_urgent_after = (surged["priority"] == "URGENT").sum()
    assert n_urgent_after > n_urgent_before


def test_caba_reassigns_when_rider_becomes_unavailable():
    """When a rider that would otherwise have taken a batch is marked
    UNAVAILABLE, the same order pool must still be handled by the remaining
    fleet without crashing, and no order should be silently lost (every
    order ends up either in a batch or in the unassigned list with a
    reason)."""
    orders = data_generator.generate_orders(n_orders=60, seed=3)
    riders = data_generator.generate_riders(n_riders=6, seed=3)

    # Run once with the full fleet
    result_full = batching_algorithm.run_caba(orders, riders)
    assigned_full = {oid for b in result_full["batches"] for oid in b.order_ids}

    # Now disable half the fleet (simulate riders becoming unavailable)
    riders_disrupted = riders.copy()
    riders_disrupted.loc[riders_disrupted.index[:3], "availability"] = "UNAVAILABLE"

    result_disrupted = batching_algorithm.run_caba(orders, riders_disrupted)
    assigned_disrupted = {oid for b in result_disrupted["batches"] for oid in b.order_ids}

    # every order must be accounted for: either assigned or explicitly unassigned
    accounted_for = assigned_disrupted | set(result_disrupted["unassigned_order_ids"])
    assert accounted_for == set(orders["order_id"])

    # disrupted fleet should never do BETTER than the full fleet in orders served
    assert len(assigned_disrupted) <= len(assigned_full) + 1e-9

    # no batch should use an unavailable rider
    unavailable_riders = set(
        riders_disrupted[riders_disrupted["availability"] == "UNAVAILABLE"]["rider_id"])
    for b in result_disrupted["batches"]:
        assert b.rider_id not in unavailable_riders


def test_caba_never_crashes_with_zero_available_riders():
    orders = data_generator.generate_orders(n_orders=20, seed=4)
    riders = data_generator.generate_riders(n_riders=5, seed=4)
    riders["availability"] = "UNAVAILABLE"

    result = batching_algorithm.run_caba(orders, riders)
    assert result["batches"] == []
    assert len(result["unassigned_order_ids"]) == 20
