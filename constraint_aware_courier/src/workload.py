"""
workload.py
===========
Frontline-worker protection module.

The project explicitly forbids optimizing distance by silently dumping extra
burden on riders. This module computes an explicit, auditable
`Rider Workload Score` (in minutes) that is reported *separately* from
distance savings, and is used by constraints.check_workload() to reject
batches that would create unreasonable working conditions.

workload_score = service_time + access_time + waiting_time + handling_time
"""

from dataclasses import dataclass
from typing import List

import pandas as pd

import config


@dataclass
class WorkloadBreakdown:
    service_time_min: float
    access_time_min: float
    waiting_time_min: float
    handling_time_min: float

    @property
    def total_minutes(self) -> float:
        return (self.service_time_min + self.access_time_min +
                self.waiting_time_min + self.handling_time_min)


def compute_waiting_time_minutes(orders: List[pd.Series], batch_start_time) -> float:
    """Total minutes a rider must wait across all orders for pickup readiness."""
    total_wait = 0.0
    for o in orders:
        ready_time = o["pickup_ready_time"]
        if ready_time > batch_start_time:
            total_wait += (ready_time - batch_start_time).total_seconds() / 60.0
    return total_wait


def compute_handling_time_minutes(orders: List[pd.Series]) -> float:
    """Extra handling minutes for fragile / heavy / frozen items (careful handling)."""
    handling = 0.0
    for o in orders:
        base = 1.0  # base handling overhead per package
        if o["fragile"]:
            base += 1.5
        if o["product_category"] == "Heavy":
            base += 2.0
        if o["product_category"] == "Frozen":
            base += 0.5  # insulated bag handling
        handling += base
    return handling


def compute_workload(orders: List[pd.Series], batch_start_time,
                      distinct_stops: int) -> WorkloadBreakdown:
    """Compute the full workload breakdown for a candidate batch."""
    service_time = sum(o["service_time_minutes"] for o in orders)
    access_time = distinct_stops * config.BUILDING_ACCESS_DELAY_MIN
    waiting_time = compute_waiting_time_minutes(orders, batch_start_time)
    handling_time = compute_handling_time_minutes(orders)

    return WorkloadBreakdown(
        service_time_min=service_time,
        access_time_min=access_time,
        waiting_time_min=waiting_time,
        handling_time_min=handling_time,
    )
