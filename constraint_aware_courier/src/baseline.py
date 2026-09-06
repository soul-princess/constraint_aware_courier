"""
baseline.py
===========
Baseline batching algorithm: simple, distance/capacity-driven,
nearest-neighbour batching.

By design this baseline does NOT fully enforce product compatibility,
pickup readiness, deadlines, or workload limits -- it represents how a naive
"just group nearby orders" system would behave. It is implemented safely
(never crashes) and every constraint it fails to honour is *recorded* as a
violation so it can be fairly compared against CABA.

Riders realistically complete MULTIPLE batches across their shift (a batch
cap like `max_orders_per_batch` caps a single trip, not the whole day), so
`run_baseline()` simulates the full operating day: each rider repeatedly
picks up a new batch, delivers it, returns, and becomes available again
until their shift ends.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

import config
from src import constraints, routing, workload

logger = logging.getLogger(__name__)

MAX_ROUNDS = 12  # safety cap on simulated pickup rounds per day


@dataclass
class Batch:
    batch_id: str
    rider_id: str
    order_ids: List[str]
    total_distance_km: float
    total_travel_time_min: float
    workload_minutes: float
    workload_band: str
    feasible: bool
    rejection_reasons: List[str] = field(default_factory=list)
    predicted_delivery_times: dict = field(default_factory=dict)


def _assign_single_round(orders: pd.DataFrame, riders: pd.DataFrame,
                          rider_available_at: Dict[str, pd.Timestamp]) -> dict:
    """Greedy nearest-neighbour clustering of a pool of (still unassigned)
    orders onto riders that are currently available, for ONE pickup round.
    Ignores compatibility, readiness, and deadlines -- capacity is the only
    hard limit enforced during assignment itself.
    """
    assignments = {r["rider_id"]: [] for _, r in riders.iterrows()}
    rider_load = {r["rider_id"]: {"weight": 0.0, "volume": 0.0, "count": 0}
                  for _, r in riders.iterrows()}
    rider_lookup = riders.set_index("rider_id")

    orders_sorted = orders.copy()
    orders_sorted["dist_from_hub"] = orders_sorted.apply(
        lambda o: routing.haversine_distance_km(
            config.HUB_LATITUDE, config.HUB_LONGITUDE, o["latitude"], o["longitude"]),
        axis=1,
    )
    orders_sorted = orders_sorted.sort_values("dist_from_hub").reset_index(drop=True)

    rider_ids = [rid for rid in rider_lookup.index if rid in rider_available_at]
    if not rider_ids:
        return assignments

    rider_cursor = 0
    for _, order in orders_sorted.iterrows():
        placed = False
        for attempt in range(len(rider_ids)):
            rid = rider_ids[(rider_cursor + attempt) % len(rider_ids)]
            rider = rider_lookup.loc[rid]
            load = rider_load[rid]
            if (load["weight"] + order["weight_kg"] <= rider["capacity_kg"] and
                    load["volume"] + order["volume_litre"] <= rider["capacity_volume"] and
                    load["count"] + 1 <= rider["max_orders_per_batch"]):
                assignments[rid].append(order)
                rider_load[rid]["weight"] += order["weight_kg"]
                rider_load[rid]["volume"] += order["volume_litre"]
                rider_load[rid]["count"] += 1
                placed = True
                rider_cursor = (rider_cursor + attempt + 1) % len(rider_ids)
                break
        if not placed:
            continue  # capacity exhausted everywhere this round

    return assignments


def _build_batch_from_orders(rider: pd.Series, rider_id: str, batch_orders: List[pd.Series],
                              batch_start_time: pd.Timestamp, batch_id: str,
                              origin_lat: float, origin_lon: float,
                              delay_multiplier: float, violations: dict):
    """Turn a raw list of orders assigned to a rider into a fully-evaluated Batch."""
    stops = [(o["location_id"], o["latitude"], o["longitude"]) for o in batch_orders]
    route = routing.estimate_batch_route(
        origin_lat, origin_lon, config.HUB_LATITUDE, config.HUB_LONGITUDE, stops,
        delay_multiplier=delay_multiplier,
    )

    distinct_stops = len({o["location_id"] for o in batch_orders})
    wl = workload.compute_workload(batch_orders, batch_start_time, distinct_stops)

    compat_result = constraints.check_batch_compatibility(batch_orders)
    if not compat_result.passed:
        violations["product"] += 1

    capacity_result = constraints.check_capacity(batch_orders, rider)
    if not capacity_result.passed:
        violations["capacity"] += 1

    readiness_result = constraints.check_pickup_readiness(batch_orders, batch_start_time)
    if not readiness_result.passed:
        violations["readiness"] += 1

    if wl.total_minutes >= config.WORKLOAD_REJECTION_THRESHOLD_MIN:
        violations["workload"] += 1

    predicted_delivery_times = {}
    cursor_time = batch_start_time
    for stop_id in route["ordered_stop_ids"]:
        matching = [o for o in batch_orders if o["location_id"] == stop_id]
        leg_time = next((d for sid, d in route["leg_distances_km"] if sid == stop_id), 0.0)
        cursor_time = cursor_time + pd.Timedelta(
            minutes=routing.travel_time_minutes(leg_time, delay_multiplier=delay_multiplier)
            + config.BUILDING_ACCESS_DELAY_MIN)
        for o in matching:
            cursor_time = cursor_time + pd.Timedelta(minutes=o["service_time_minutes"])
            predicted_delivery_times[o["order_id"]] = cursor_time
            deadline_check = constraints.check_deadline_feasibility(o, cursor_time)
            if not deadline_check.passed:
                violations["deadline"] += 1

    batch = Batch(
        batch_id=batch_id,
        rider_id=rider_id,
        order_ids=[o["order_id"] for o in batch_orders],
        total_distance_km=route["total_distance_km"],
        total_travel_time_min=route["total_travel_time_min"],
        workload_minutes=wl.total_minutes,
        workload_band=constraints.classify_workload(wl.total_minutes),
        feasible=True,  # baseline always "accepts" its own batches
        rejection_reasons=[],
        predicted_delivery_times=predicted_delivery_times,
    )
    return batch, route


def run_baseline(orders: pd.DataFrame, riders: pd.DataFrame,
                  delay_multiplier: float = 1.0) -> dict:
    """Run the baseline algorithm across the FULL operating day.

    Each rider is repeatedly given a new pickup round (bounded by their
    shift window) until either no orders remain or no rider has time left.

    Returns a dict with: batches (list[Batch]), unassigned_order_ids,
    violation counts, and total distance.
    """
    riders_avail = riders[riders["availability"] == "AVAILABLE"].copy()
    rider_lookup = riders_avail.set_index("rider_id")

    rider_available_at = {rid: r["shift_start"] for rid, r in rider_lookup.iterrows()}
    rider_position = {rid: (r["current_latitude"], r["current_longitude"])
                       for rid, r in rider_lookup.iterrows()}

    remaining_orders = orders.copy()
    batches: List[Batch] = []
    violations = {"deadline": 0, "capacity": 0, "product": 0, "readiness": 0, "workload": 0}
    assigned_ids = set()
    batch_counter = 1

    for round_num in range(MAX_ROUNDS):
        if remaining_orders.empty:
            break

        active_riders = [rid for rid in rider_lookup.index
                          if rider_available_at[rid] < rider_lookup.loc[rid, "shift_end"]]
        if not active_riders:
            break

        active_riders_df = rider_lookup.loc[active_riders].reset_index()
        assignments = _assign_single_round(
            remaining_orders, active_riders_df,
            {rid: rider_available_at[rid] for rid in active_riders})

        any_progress = False
        for rider_id, batch_orders in assignments.items():
            if not batch_orders:
                continue
            any_progress = True
            rider = rider_lookup.loc[rider_id]
            origin_lat, origin_lon = rider_position[rider_id]
            batch_start_time = max(rider_available_at[rider_id],
                                    min(o["pickup_ready_time"] for o in batch_orders))

            batch, route = _build_batch_from_orders(
                rider, rider_id, batch_orders, batch_start_time,
                f"BASE-B{batch_counter:04d}", origin_lat, origin_lon,
                delay_multiplier, violations)
            batches.append(batch)
            assigned_ids.update(batch.order_ids)
            batch_counter += 1

            rider_available_at[rider_id] = batch_start_time + pd.Timedelta(
                minutes=route["total_travel_time_min"])
            last_stop = batch_orders[-1]
            rider_position[rider_id] = (last_stop["latitude"], last_stop["longitude"])

        remaining_orders = remaining_orders[~remaining_orders["order_id"].isin(assigned_ids)]
        if not any_progress:
            break

    unassigned = [oid for oid in orders["order_id"] if oid not in assigned_ids]
    total_distance = sum(b.total_distance_km for b in batches)

    logger.info("Baseline: %d batches, %d unassigned orders, total distance %.2f km",
                len(batches), len(unassigned), total_distance)

    return {
        "batches": batches,
        "unassigned_order_ids": unassigned,
        "violations": violations,
        "total_distance_km": total_distance,
    }
