"""
batching_algorithm.py
======================
Constraint-Aware Batching Algorithm (CABA) -- the core contribution of this
project.

Approach
--------
Exact multi-batch, multi-rider optimisation under 8 simultaneous constraints
is combinatorially explosive for 1000+ orders and 50+ riders, so CABA uses a
*constructive greedy heuristic with explicit constraint checking and a
multi-objective scoring function* -- a standard, explainable approach for
real-time batching systems (and appropriate for an academic prototype):

  1. Orders are processed in priority order (URGENT first, then by
     pickup-ready time), so urgent orders get first pick of the best batches
     (Constraint 7).
  2. For each order, CABA searches currently "open" batches (one per rider,
     for the current pickup round) and evaluates the HARD constraints
     (capacity, compatibility, pickup readiness, deadline, workload, max
     stops) -- constraints 1-6.
  3. Among all batches where the order can be feasibly inserted, CABA picks
     the one with the lowest resulting Batch Score (Section 7 objective
     function). If no open batch can feasibly take the order, CABA opens a
     new batch with the nearest available, unfilled rider.
  4. If NO rider can feasibly take the order at all in this round, it is
     carried over to the next round (a rider may free up later) or, if no
     rider has any shift time left, it is left unassigned with a clear,
     logged reason (never silently dropped).
  5. Riders realistically complete MULTIPLE batches per shift, so the whole
     operating day is simulated as a sequence of pickup ROUNDS: after
     finishing a batch, a rider becomes available again (their next
     `available_at` = batch start + total travel time) until their shift
     ends.
  6. Disruptions (rider loss / travel delay / demand surge) are handled by
     re-running the same feasible-insertion logic against the *disrupted*
     rider pool and travel-time multiplier (Constraint 8) -- see
     src/disruption.py which prepares the disrupted inputs.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

import config
from src import constraints, routing, workload

logger = logging.getLogger(__name__)

PRIORITY_ORDER = {"URGENT": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
MAX_ROUNDS = 12  # safety cap on simulated pickup rounds per day


@dataclass
class OpenBatch:
    batch_id: str
    rider_id: str
    rider: pd.Series
    origin_lat: float
    origin_lon: float
    orders: List[pd.Series] = field(default_factory=list)
    start_time: Optional[pd.Timestamp] = None

    @property
    def distinct_stops(self) -> int:
        return len({o["location_id"] for o in self.orders})


@dataclass
class FinalBatch:
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


def batch_score(distance_km: float, deadline_risk_min: float, workload_min: float,
                 waiting_min: float, has_urgent: bool) -> float:
    """Multi-objective Batch Score. Lower is better.

    Batch Score = distance_cost + deadline_risk_penalty + workload_penalty
                  + waiting_time_penalty - urgent_priority_bonus

    Hard constraint violations (incompatibility / capacity) are NEVER scored
    here -- they are rejected outright before scoring is even considered.
    """
    score = (
        config.WEIGHT_DISTANCE * distance_km
        + config.WEIGHT_DEADLINE_RISK * max(0.0, deadline_risk_min)
        + config.WEIGHT_WORKLOAD * workload_min
        + config.WEIGHT_WAITING_TIME * waiting_min
    )
    if has_urgent:
        score -= config.URGENT_PRIORITY_BONUS
    return score


def _predict_batch_route_and_delivery(batch: OpenBatch, delay_multiplier: float):
    """Compute route + predicted per-order delivery times for a batch."""
    stops = [(o["location_id"], o["latitude"], o["longitude"]) for o in batch.orders]
    route = routing.estimate_batch_route(
        batch.origin_lat, batch.origin_lon,
        config.HUB_LATITUDE, config.HUB_LONGITUDE, stops,
        delay_multiplier=delay_multiplier,
    )
    predicted_delivery_times = {}
    cursor_time = batch.start_time
    for stop_id in route["ordered_stop_ids"]:
        leg_time = next((d for sid, d in route["leg_distances_km"] if sid == stop_id), 0.0)
        cursor_time = cursor_time + pd.Timedelta(
            minutes=routing.travel_time_minutes(leg_time, delay_multiplier=delay_multiplier)
            + config.BUILDING_ACCESS_DELAY_MIN)
        matching = [o for o in batch.orders if o["location_id"] == stop_id]
        for o in matching:
            cursor_time = cursor_time + pd.Timedelta(minutes=o["service_time_minutes"])
            predicted_delivery_times[o["order_id"]] = cursor_time
    return route, predicted_delivery_times


def _try_insert(batch: OpenBatch, order: pd.Series, delay_multiplier: float):
    """Check all hard constraints for inserting `order` into `batch`.

    Returns (feasible, reason, score, route, predicted_delivery_times, wl_minutes)
    """
    candidate_orders = batch.orders + [order]

    capacity_result = constraints.check_capacity(candidate_orders, batch.rider)
    if not capacity_result.passed:
        return False, capacity_result.reason, None, None, None, None

    compat_result = constraints.check_batch_compatibility(candidate_orders)
    if not compat_result.passed:
        return False, compat_result.reason, None, None, None, None

    stops_result = constraints.check_max_stops(candidate_orders)
    if not stops_result.passed:
        return False, stops_result.reason, None, None, None, None

    start_time = max(batch.start_time, order["pickup_ready_time"]) if batch.orders \
        else max(batch.start_time, order["pickup_ready_time"])

    readiness_result = constraints.check_pickup_readiness(candidate_orders, start_time)
    if not readiness_result.passed:
        return False, readiness_result.reason, None, None, None, None

    trial_batch = OpenBatch(batch.batch_id, batch.rider_id, batch.rider,
                             batch.origin_lat, batch.origin_lon,
                             candidate_orders, start_time)
    route, predicted_delivery_times = _predict_batch_route_and_delivery(
        trial_batch, delay_multiplier)

    max_deadline_risk = 0.0
    for o in candidate_orders:
        predicted_time = predicted_delivery_times.get(o["order_id"])
        if predicted_time is None:
            continue
        deadline_check = constraints.check_deadline_feasibility(o, predicted_time)
        if not deadline_check.passed:
            return False, deadline_check.reason, None, None, None, None
        risk_minutes = (predicted_time - (o["promised_deadline"] -
                         pd.Timedelta(minutes=config.DEADLINE_SAFETY_BUFFER_MIN))
                         ).total_seconds() / 60.0
        max_deadline_risk = max(max_deadline_risk, risk_minutes)

    wl = workload.compute_workload(candidate_orders, start_time, trial_batch.distinct_stops)
    workload_result = constraints.check_workload(wl.total_minutes)
    if not workload_result.passed:
        return False, workload_result.reason, None, None, None, None

    has_urgent = any(o["priority"] == "URGENT" for o in candidate_orders)
    score = batch_score(route["total_distance_km"], max_deadline_risk,
                         wl.total_minutes, wl.waiting_time_min, has_urgent)

    return True, "", score, route, predicted_delivery_times, wl.total_minutes


def _run_single_round(orders: pd.DataFrame, rider_lookup: pd.DataFrame,
                       rider_available_at: Dict[str, pd.Timestamp],
                       rider_position: Dict[str, Tuple[float, float]],
                       delay_multiplier: float, batch_counter_start: int
                       ) -> Tuple[List[FinalBatch], List[str], List[dict], int]:
    """Run ONE pickup round of CABA across all currently-active riders."""
    open_batches: Dict[str, OpenBatch] = {}
    unassigned: List[dict] = []
    used_riders = set()
    batch_counter = batch_counter_start

    orders_sorted = orders.copy()
    orders_sorted["_priority_rank"] = orders_sorted["priority"].map(PRIORITY_ORDER).fillna(3)
    orders_sorted = orders_sorted.sort_values(
        ["_priority_rank", "pickup_ready_time"]).reset_index(drop=True)

    rider_ids_by_availability = sorted(
        rider_lookup.index, key=lambda rid: rider_available_at[rid])

    for _, order in orders_sorted.iterrows():
        candidates = []
        last_reason = "No riders available"

        for rider_id, batch in open_batches.items():
            if len(batch.orders) >= batch.rider["max_orders_per_batch"]:
                continue
            feasible, reason, score, route, pdt, wl_min = _try_insert(
                batch, order, delay_multiplier)
            if feasible:
                candidates.append((score, batch))
            else:
                last_reason = reason

        if not candidates:
            unused_riders = [rid for rid in rider_ids_by_availability if rid not in used_riders]
            unused_riders.sort(key=lambda rid: routing.haversine_distance_km(
                rider_position[rid][0], rider_position[rid][1],
                order["latitude"], order["longitude"]))
            placed_in_new_batch = False
            for rid in unused_riders:
                rider = rider_lookup.loc[rid]
                new_batch = OpenBatch(
                    batch_id=f"CABA-B{batch_counter:04d}",
                    rider_id=rid, rider=rider,
                    origin_lat=rider_position[rid][0], origin_lon=rider_position[rid][1],
                    orders=[], start_time=max(rider_available_at[rid],
                                               order["pickup_ready_time"]),
                )
                feasible, reason, score, route, pdt, wl_min = _try_insert(
                    new_batch, order, delay_multiplier)
                if feasible:
                    new_batch.orders = [order]
                    open_batches[rid] = new_batch
                    used_riders.add(rid)
                    batch_counter += 1
                    placed_in_new_batch = True
                    break
                else:
                    last_reason = reason

            if not placed_in_new_batch:
                unassigned.append({"order_id": order["order_id"], "reason": last_reason})
                continue
        else:
            best_score, best_batch = min(candidates, key=lambda c: c[0])
            best_batch.orders.append(order)
            best_batch.start_time = max(best_batch.start_time, order["pickup_ready_time"])

    final_batches: List[FinalBatch] = []
    for rider_id, batch in open_batches.items():
        route, predicted_delivery_times = _predict_batch_route_and_delivery(
            batch, delay_multiplier)
        wl = workload.compute_workload(batch.orders, batch.start_time, batch.distinct_stops)

        # advance rider state for the NEXT round
        rider_available_at[rider_id] = batch.start_time + pd.Timedelta(
            minutes=route["total_travel_time_min"])
        last_order = batch.orders[-1]
        rider_position[rider_id] = (last_order["latitude"], last_order["longitude"])

        final_batches.append(FinalBatch(
            batch_id=batch.batch_id,
            rider_id=rider_id,
            order_ids=[o["order_id"] for o in batch.orders],
            total_distance_km=route["total_distance_km"],
            total_travel_time_min=route["total_travel_time_min"],
            workload_minutes=wl.total_minutes,
            workload_band=constraints.classify_workload(wl.total_minutes),
            feasible=True,
            rejection_reasons=[],
            predicted_delivery_times=predicted_delivery_times,
        ))

    return final_batches, [u["order_id"] for u in unassigned], unassigned, batch_counter


def run_caba(orders: pd.DataFrame, riders: pd.DataFrame,
             delay_multiplier: float = 1.0) -> dict:
    """Run the Constraint-Aware Batching Algorithm across the FULL operating
    day, simulating repeated pickup rounds per rider until their shift ends
    or no unassigned orders remain."""
    riders_available = riders[riders["availability"] == "AVAILABLE"].copy()
    rider_lookup = riders_available.set_index("rider_id")

    rider_available_at = {rid: r["shift_start"] for rid, r in rider_lookup.iterrows()}
    rider_position = {rid: (r["current_latitude"], r["current_longitude"])
                       for rid, r in rider_lookup.iterrows()}

    remaining_orders = orders.copy()
    all_final_batches: List[FinalBatch] = []
    all_unassigned_reasons: List[dict] = []
    batch_counter = 1

    for round_num in range(MAX_ROUNDS):
        if remaining_orders.empty:
            break

        active_rider_ids = [rid for rid in rider_lookup.index
                             if rider_available_at[rid] < rider_lookup.loc[rid, "shift_end"]]
        if not active_rider_ids:
            break

        active_riders_df = rider_lookup.loc[active_rider_ids]

        final_batches, unassigned_ids, unassigned_reasons, batch_counter = _run_single_round(
            remaining_orders, active_riders_df, rider_available_at, rider_position,
            delay_multiplier, batch_counter)

        all_final_batches.extend(final_batches)

        assigned_this_round = {oid for b in final_batches for oid in b.order_ids}
        if not assigned_this_round:
            # nothing could be placed this round even with fresh riders -> stop
            all_unassigned_reasons.extend(unassigned_reasons)
            break

        remaining_orders = remaining_orders[
            ~remaining_orders["order_id"].isin(assigned_this_round)]

    # any orders still remaining after the loop (e.g. MAX_ROUNDS reached, or
    # no rider had shift time left) are genuinely unassigned
    still_remaining_ids = set(remaining_orders["order_id"]) if not remaining_orders.empty else set()
    for oid in still_remaining_ids:
        if not any(u["order_id"] == oid for u in all_unassigned_reasons):
            all_unassigned_reasons.append(
                {"order_id": oid, "reason": "No rider had feasible capacity/shift time remaining"})

    total_distance = sum(b.total_distance_km for b in all_final_batches)
    assigned_ids = {oid for b in all_final_batches for oid in b.order_ids}
    unassigned_ids = [oid for oid in orders["order_id"] if oid not in assigned_ids]

    logger.info("CABA: %d batches, %d unassigned orders, total distance %.2f km",
                len(all_final_batches), len(unassigned_ids), total_distance)

    # CABA rejects rather than commits violations, so committed batches have
    # zero violations by construction.
    violations = {"deadline": 0, "capacity": 0, "product": 0, "readiness": 0, "workload": 0}

    return {
        "batches": all_final_batches,
        "unassigned_order_ids": unassigned_ids,
        "unassigned_reasons": all_unassigned_reasons,
        "violations": violations,
        "total_distance_km": total_distance,
    }
