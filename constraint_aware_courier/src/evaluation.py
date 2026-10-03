"""
evaluation.py
=============
Computes the full metric set required to compare the baseline against CABA,
for both normal and disrupted scenarios (Sections 10, 11, 13 of the spec).
"""

import time
from typing import Dict, List

import pandas as pd

import config
from src import baseline as baseline_mod
from src import batching_algorithm as caba_mod


def _urgent_on_time_rate(orders: pd.DataFrame, result: dict) -> float:
    """Fraction of URGENT orders that were both assigned and delivered on time."""
    urgent_ids = set(orders[orders["priority"] == "URGENT"]["order_id"])
    if not urgent_ids:
        return 1.0
    orders_by_id = orders.set_index("order_id")
    on_time = 0
    for batch in result["batches"]:
        for oid, delivered_at in batch.predicted_delivery_times.items():
            if oid in urgent_ids:
                deadline = orders_by_id.loc[oid, "promised_deadline"]
                if delivered_at <= deadline:
                    on_time += 1
    return on_time / len(urgent_ids)


def _on_time_rate(orders: pd.DataFrame, result: dict) -> float:
    orders_by_id = orders.set_index("order_id")
    total_delivered = 0
    on_time = 0
    for batch in result["batches"]:
        for oid, delivered_at in batch.predicted_delivery_times.items():
            total_delivered += 1
            deadline = orders_by_id.loc[oid, "promised_deadline"]
            if delivered_at <= deadline:
                on_time += 1
    return (on_time / total_delivered) if total_delivered else 0.0


def run_algorithm_with_timing(algo_name: str, orders: pd.DataFrame, riders: pd.DataFrame,
                               delay_multiplier: float = 1.0) -> dict:
    """Run either 'baseline' or 'caba' and time its execution."""
    start = time.perf_counter()
    if algo_name == "baseline":
        result = baseline_mod.run_baseline(orders, riders, delay_multiplier=delay_multiplier)
    elif algo_name == "caba":
        result = caba_mod.run_caba(orders, riders, delay_multiplier=delay_multiplier)
    else:
        raise ValueError(f"Unknown algorithm: {algo_name}")
    elapsed = time.perf_counter() - start
    result["execution_time_sec"] = elapsed
    return result


def summarise_result(orders: pd.DataFrame, result: dict) -> dict:
    """Compute the full metric dictionary for a single algorithm run."""
    batches = result["batches"]
    n_batches = len(batches)
    total_orders_in_batches = sum(len(b.order_ids) for b in batches)
    avg_batch_size = (total_orders_in_batches / n_batches) if n_batches else 0.0

    workloads = [b.workload_minutes for b in batches] if batches else [0.0]

    metrics = {
        "total_distance_km": result["total_distance_km"],
        "average_distance_per_order_km": (
            result["total_distance_km"] / total_orders_in_batches
            if total_orders_in_batches else 0.0),
        "num_batches": n_batches,
        "average_batch_size": avg_batch_size,
        "deadline_violations": result["violations"]["deadline"],
        "product_violations": result["violations"]["product"],
        "capacity_violations": result["violations"]["capacity"],
        "readiness_violations": result["violations"]["readiness"],
        "workload_violations": result["violations"]["workload"],
        "average_rider_workload_min": sum(workloads) / len(workloads),
        "maximum_rider_workload_min": max(workloads),
        "orders_assigned": total_orders_in_batches,
        "unassigned_orders": len(result["unassigned_order_ids"]),
        "on_time_delivery_rate": _on_time_rate(orders, result),
        "urgent_on_time_rate": _urgent_on_time_rate(orders, result),
        "execution_time_sec": result.get("execution_time_sec", None),
    }
    return metrics


def compare_algorithms(orders: pd.DataFrame, riders: pd.DataFrame,
                        delay_multiplier: float = 1.0) -> Dict[str, dict]:
    """Run both baseline and CABA on the SAME input data and return metrics
    for each, plus a computed comparison table."""
    baseline_result = run_algorithm_with_timing("baseline", orders, riders, delay_multiplier)
    caba_result = run_algorithm_with_timing("caba", orders, riders, delay_multiplier)

    baseline_metrics = summarise_result(orders, baseline_result)
    caba_metrics = summarise_result(orders, caba_result)

    distance_saved = baseline_metrics["total_distance_km"] - caba_metrics["total_distance_km"]
    distance_saved_pct = (
        (distance_saved / baseline_metrics["total_distance_km"]) * 100.0
        if baseline_metrics["total_distance_km"] > 0 else 0.0
    )

    comparison_rows = []
    metric_labels = [
        ("total_distance_km", "Total Distance (km)"),
        ("average_distance_per_order_km", "Avg Distance / Order (km)"),
        ("num_batches", "Number of Batches"),
        ("average_batch_size", "Average Batch Size"),
        ("deadline_violations", "Deadline Violations"),
        ("product_violations", "Product Incompatibility Violations"),
        ("capacity_violations", "Capacity Violations"),
        ("readiness_violations", "Pickup Readiness Violations"),
        ("workload_violations", "Workload Violations"),
        ("average_rider_workload_min", "Average Rider Workload (min)"),
        ("maximum_rider_workload_min", "Maximum Rider Workload (min)"),
        ("on_time_delivery_rate", "On-Time Delivery Rate"),
        ("urgent_on_time_rate", "Urgent Order On-Time Rate"),
        ("unassigned_orders", "Unassigned Orders"),
        ("execution_time_sec", "Execution Time (sec)"),
    ]
    for key, label in metric_labels:
        b_val = baseline_metrics[key]
        c_val = caba_metrics[key]
        if isinstance(b_val, (int, float)) and isinstance(c_val, (int, float)) and b_val != 0:
            improvement = ((b_val - c_val) / abs(b_val)) * 100.0
        else:
            improvement = None
        comparison_rows.append({
            "Metric": label,
            "Baseline": round(b_val, 3) if isinstance(b_val, float) else b_val,
            "CABA": round(c_val, 3) if isinstance(c_val, float) else c_val,
            "Improvement (%)": round(improvement, 2) if improvement is not None else "N/A",
        })

    comparison_df = pd.DataFrame(comparison_rows)

    return {
        "baseline_result": baseline_result,
        "caba_result": caba_result,
        "baseline_metrics": baseline_metrics,
        "caba_metrics": caba_metrics,
        "distance_saved_km": distance_saved,
        "distance_saved_pct": distance_saved_pct,
        "comparison_table": comparison_df,
    }
