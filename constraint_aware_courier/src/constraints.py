"""
constraints.py
===============
Reusable constraint-checking system for the courier batching project.

Design goal (per project spec): compatibility logic must NOT be hard-coded
inside a single monolithic function. Instead:

  * `COMPATIBILITY_MATRIX` is a data-driven, configurable lookup table.
  * `GROUP_CONFLICTS` handles fine-grained SKU/group-level conflicts that
    are not captured by broad category alone.
  * Each hard constraint (capacity, compatibility, readiness, deadline,
    workload, stops) is implemented as its own small, testable function
    returning a `ConstraintResult` (a pass/fail + explanation), so callers
    always know *why* an order or batch was rejected.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pandas as pd

import config

# ---------------------------------------------------------------------------
# Compatibility matrix (symmetric). True = allowed together.
# ---------------------------------------------------------------------------
COMPATIBILITY_MATRIX = {
    ("Normal", "Normal"): True,
    ("Normal", "Fragile"): True,
    ("Normal", "Heavy"): True,
    ("Normal", "Frozen"): True,
    ("Normal", "Hot Food"): True,
    ("Normal", "Chemical"): False,

    ("Fragile", "Fragile"): True,
    ("Fragile", "Heavy"): False,     # heavy items can crush fragile items
    ("Fragile", "Frozen"): True,
    ("Fragile", "Hot Food"): True,
    ("Fragile", "Chemical"): False,

    ("Heavy", "Heavy"): True,
    ("Heavy", "Frozen"): True,
    ("Heavy", "Hot Food"): True,
    ("Heavy", "Chemical"): False,

    ("Frozen", "Frozen"): True,
    ("Frozen", "Hot Food"): False,   # temperature conflict
    ("Frozen", "Chemical"): False,

    ("Hot Food", "Hot Food"): True,
    ("Hot Food", "Chemical"): False,

    ("Chemical", "Chemical"): True,  # only with other chemicals, carefully packed
}


def _lookup_compatibility(cat_a: str, cat_b: str) -> bool:
    key = (cat_a, cat_b)
    if key in COMPATIBILITY_MATRIX:
        return COMPATIBILITY_MATRIX[key]
    key_rev = (cat_b, cat_a)
    if key_rev in COMPATIBILITY_MATRIX:
        return COMPATIBILITY_MATRIX[key_rev]
    # Unknown combination: fail safe -> not allowed, must be explicitly configured.
    return False


# Fine-grained group conflicts: any two DIFFERENT non-null groups sharing the
# same prefix (e.g. "CHE-G1" vs "CHE-G2") represent products that cannot be
# transported together even though they share a broad category.
def _groups_conflict(group_a: Optional[str], group_b: Optional[str]) -> bool:
    if group_a is None or group_b is None or pd.isna(group_a) or pd.isna(group_b):
        return False
    prefix_a, prefix_b = group_a.split("-")[0], group_b.split("-")[0]
    return prefix_a == prefix_b and group_a != group_b


@dataclass
class ConstraintResult:
    """Result of a single constraint check."""
    passed: bool
    reason: str = ""


def check_pair_compatibility(order_a: pd.Series, order_b: pd.Series) -> ConstraintResult:
    """Check whether two individual orders are compatible with each other."""
    cat_a, cat_b = order_a["product_category"], order_b["product_category"]
    if not _lookup_compatibility(cat_a, cat_b):
        return ConstraintResult(
            False,
            f"Product incompatibility: {cat_a} and {cat_b} "
            f"({order_a['order_id']} + {order_b['order_id']})",
        )
    if _groups_conflict(order_a.get("incompatible_group"), order_b.get("incompatible_group")):
        return ConstraintResult(
            False,
            f"Group-level incompatibility: {order_a['incompatible_group']} vs "
            f"{order_b['incompatible_group']} ({order_a['order_id']} + {order_b['order_id']})",
        )
    return ConstraintResult(True)


def check_batch_compatibility(orders: List[pd.Series]) -> ConstraintResult:
    """Check ALL pairwise combinations of orders in a candidate batch."""
    for i in range(len(orders)):
        for j in range(i + 1, len(orders)):
            result = check_pair_compatibility(orders[i], orders[j])
            if not result.passed:
                return result
    return ConstraintResult(True)


def check_capacity(orders: List[pd.Series], rider: pd.Series) -> ConstraintResult:
    """Check total weight/volume of a batch against rider capacity."""
    total_weight = sum(o["weight_kg"] for o in orders)
    total_volume = sum(o["volume_litre"] for o in orders)
    if total_weight > rider["capacity_kg"]:
        return ConstraintResult(
            False,
            f"Capacity exceeded: total weight {total_weight:.2f}kg > "
            f"rider capacity {rider['capacity_kg']}kg",
        )
    if total_volume > rider["capacity_volume"]:
        return ConstraintResult(
            False,
            f"Capacity exceeded: total volume {total_volume:.2f}L > "
            f"rider capacity {rider['capacity_volume']}L",
        )
    if len(orders) > rider["max_orders_per_batch"]:
        return ConstraintResult(
            False,
            f"Order count exceeded: {len(orders)} orders > "
            f"rider max_orders_per_batch {rider['max_orders_per_batch']}",
        )
    return ConstraintResult(True)


def check_pickup_readiness(orders: List[pd.Series], batch_start_time: datetime,
                            max_wait_min: float = config.MAX_WAITING_TIME_MIN
                            ) -> ConstraintResult:
    """An order should not force a rider to wait excessively for pickup."""
    for o in orders:
        ready_time = o["pickup_ready_time"]
        if ready_time > batch_start_time:
            wait_minutes = (ready_time - batch_start_time).total_seconds() / 60.0
            if wait_minutes > max_wait_min:
                return ConstraintResult(
                    False,
                    f"Pickup readiness violation: {o['order_id']} not ready for "
                    f"{wait_minutes:.1f} min (max allowed wait {max_wait_min} min)",
                )
    return ConstraintResult(True)


def check_deadline_feasibility(order: pd.Series, predicted_delivery_time: datetime,
                                safety_buffer_min: float = config.DEADLINE_SAFETY_BUFFER_MIN
                                ) -> ConstraintResult:
    """Check whether a single order's predicted delivery beats its deadline."""
    deadline_with_buffer = order["promised_deadline"] - pd.Timedelta(minutes=safety_buffer_min)
    if predicted_delivery_time > deadline_with_buffer:
        late_by = (predicted_delivery_time - order["promised_deadline"]).total_seconds() / 60.0
        return ConstraintResult(
            False,
            f"Deadline violation: {order['order_id']} predicted delivery "
            f"{predicted_delivery_time} misses promised deadline "
            f"{order['promised_deadline']} (late by {late_by:.1f} min incl. buffer)",
        )
    return ConstraintResult(True)


def check_workload(workload_minutes: float,
                    threshold: float = config.WORKLOAD_REJECTION_THRESHOLD_MIN
                    ) -> ConstraintResult:
    """Reject a batch if predicted rider workload exceeds the operational threshold."""
    if workload_minutes >= threshold:
        return ConstraintResult(
            False,
            f"Workload violation: predicted workload {workload_minutes:.1f} min "
            f">= threshold {threshold} min",
        )
    return ConstraintResult(True)


def check_max_stops(orders: List[pd.Series],
                     max_stops: int = config.MAX_STOPS_PER_BATCH) -> ConstraintResult:
    """Limit the number of distinct buildings/stops in a single batch."""
    distinct_locations = {o["location_id"] for o in orders}
    if len(distinct_locations) > max_stops:
        return ConstraintResult(
            False,
            f"Max stops violation: {len(distinct_locations)} distinct stops > "
            f"limit {max_stops}",
        )
    return ConstraintResult(True)


def classify_workload(workload_minutes: float) -> str:
    """Map a workload figure (minutes) to a LOW/MEDIUM/HIGH/EXCESSIVE band."""
    for band, (low, high) in config.WORKLOAD_BANDS.items():
        if low <= workload_minutes < high:
            return band
    return "EXCESSIVE"
