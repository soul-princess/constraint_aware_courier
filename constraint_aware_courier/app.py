"""
app.py
======
Streamlit application for the Constraint-Aware Courier Batching project.

Run with:
    streamlit run app.py
"""

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from src import preprocessing, disruption, evaluation, visualization, data_generator

st.set_page_config(page_title="Constraint-Aware Courier Batching (CABA)", layout="wide")

SCENARIO_OPTIONS = {
    "Normal Day": "normal",
    "Rider Capacity Loss": "rider_loss",
    "Travel Delay": "travel_delay",
    "Urgent Demand": "urgent_surge",
}


@st.cache_data(show_spinner=False)
def _load_base_data():
    if not (os.path.exists(config.ORDERS_FILE) and os.path.exists(config.RIDERS_FILE)):
        data_generator.generate_and_save()
    return preprocessing.load_dataset()


@st.cache_data(show_spinner="Running algorithms for this scenario...")
def _run_scenario(scenario_key: str):
    orders_raw, riders_raw = _load_base_data()
    orders, riders, delay_multiplier = disruption.apply_scenario(scenario_key, orders_raw, riders_raw)
    comparison = evaluation.compare_algorithms(orders, riders, delay_multiplier)
    return orders, riders, comparison


def _batches_to_dataframe(batches, orders_lookup):
    rows = []
    for b in batches:
        rows.append({
            "Batch ID": b.batch_id,
            "Rider": b.rider_id,
            "Orders": ", ".join(b.order_ids),
            "# Orders": len(b.order_ids),
            "Distance (km)": round(b.total_distance_km, 2),
            "Est. Duration (min)": round(b.total_travel_time_min, 1),
            "Workload (min)": round(b.workload_minutes, 1),
            "Workload Band": b.workload_band,
            "Feasible": "Yes" if b.feasible else "No",
        })
    return pd.DataFrame(rows)


<<<<<<< HEAD
def _side_by_side_workflow_table(baseline_metrics, caba_metrics, baseline_batches, caba_batches):
    """Builds the BASELINE vs PROPOSED side-by-side comparison requested in
    the reviewer feedback: stops, route time, distance, orders, workload --
    all from ACTUAL measured values, never example numbers."""
    def _total_route_minutes(batches):
        return sum(b.total_travel_time_min for b in batches)

    rows = [
        {"Metric": "Batches (Stops Groups)", "Baseline": len(baseline_batches), "Proposed (CABA)": len(caba_batches)},
        {"Metric": "Total Route Time (min)", "Baseline": round(_total_route_minutes(baseline_batches), 1),
         "Proposed (CABA)": round(_total_route_minutes(caba_batches), 1)},
        {"Metric": "Total Distance (km)", "Baseline": round(baseline_metrics["total_distance_km"], 1),
         "Proposed (CABA)": round(caba_metrics["total_distance_km"], 1)},
        {"Metric": "Orders Served", "Baseline": baseline_metrics["orders_assigned"],
         "Proposed (CABA)": caba_metrics["orders_assigned"]},
        {"Metric": "Avg Rider Workload (min)", "Baseline": round(baseline_metrics["average_rider_workload_min"], 1),
         "Proposed (CABA)": round(caba_metrics["average_rider_workload_min"], 1)},
        {"Metric": "Max Rider Workload (min)", "Baseline": round(baseline_metrics["maximum_rider_workload_min"], 1),
         "Proposed (CABA)": round(caba_metrics["maximum_rider_workload_min"], 1)},
    ]
    return pd.DataFrame(rows)


def _rejection_reasons_dataframe(caba_result):
    """Builds the 'Why was this order rejected?' table requested in the
    reviewer feedback, using the REAL unassigned_reasons / recovery_log
    produced by CABA -- not fabricated examples."""
    rows = []

    # map order -> short reason category for readability
    def _short_reason(reason: str) -> str:
        if "Capacity exceeded" in reason:
            return "Capacity exceeded"
        if "Deadline violation" in reason:
            return "Deadline violation"
        if "incompatibility" in reason or "Group-level" in reason:
            return "Product incompatible"
        if "Pickup readiness" in reason:
            return "Pickup not ready"
        if "Workload violation" in reason:
            return "Workload limit"
        if "Max stops" in reason:
            return "Too many stops"
        return reason[:40] if reason else "Unknown"

    recovery_by_id = {t["order_id"]: t for t in caba_result.get("recovery_log", [])}

    for u in caba_result.get("unassigned_reasons", []):
        oid = u["order_id"]
        was_attempted_in_recovery = oid in recovery_by_id
        rows.append({
            "Order": oid,
            "Result": "Rejected",
            "Reason": _short_reason(u["reason"]),
            "Recovery Attempted": "Yes (still infeasible)" if was_attempted_in_recovery else "No",
            "Full Detail": u["reason"],
        })
    return pd.DataFrame(rows)


=======
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
def _orders_to_dataframe(orders, batches):
    order_to_batch = {}
    order_to_rider = {}
    for b in batches:
        for oid in b.order_ids:
            order_to_batch[oid] = b.batch_id
            order_to_rider[oid] = b.rider_id

    rows = []
    for _, o in orders.iterrows():
        rows.append({
            "Order ID": o["order_id"],
            "Location": o["building_name"],
            "Product": o["product_category"],
            "Deadline": o["promised_deadline"],
            "Ready Time": o["pickup_ready_time"],
            "Weight (kg)": o["weight_kg"],
            "Priority": o["priority"],
            "Assigned Rider": order_to_rider.get(o["order_id"], "-"),
            "Batch ID": order_to_batch.get(o["order_id"], "-"),
            "Status": "Assigned" if o["order_id"] in order_to_batch else "Unassigned",
        })
    return pd.DataFrame(rows)


def main():
    st.title("🚚 Constraint-Aware Courier Batching System (CABA)")
    st.caption(
        "Constraint-Aware Batching Algorithm for Time-Sensitive and Incompatible "
        "E-Commerce Courier Deliveries -- academic prototype."
    )

    with st.sidebar:
        st.header("Controls")
        scenario_label = st.selectbox("Scenario", list(SCENARIO_OPTIONS.keys()))
        algo_view = st.selectbox("Algorithm View", ["Compare Both", "Baseline", "Constraint-Aware (CABA)"])
        st.markdown("---")
<<<<<<< HEAD
        st.markdown(f"**Routing provider:** `{config.ROUTING_PROVIDER}`")
        st.markdown(
            "**Note:** This is a simulation using synthetic data and "
            "Haversine-distance routing -- not a live GPS/traffic feed. "
            "The routing layer is pluggable (see `src/routing.py`) with a "
            "documented, unimplemented OSRM hook for future real road "
            "routing. See `docs/limitations.md` for details."
=======
        st.markdown(
            "**Note:** This is a simulation using synthetic data and "
            "Haversine-distance routing -- not a live GPS/traffic feed. "
            "See `docs/limitations.md` for details."
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
        )

    scenario_key = SCENARIO_OPTIONS[scenario_label]
    orders, riders, comparison = _run_scenario(scenario_key)

    baseline_metrics = comparison["baseline_metrics"]
    caba_metrics = comparison["caba_metrics"]

    # ---------------------------------------------------------------
    # Dashboard
    # ---------------------------------------------------------------
    st.subheader("📊 Dashboard")
    active_metrics = caba_metrics if algo_view != "Baseline" else baseline_metrics
    active_batches = (comparison["caba_result"]["batches"] if algo_view != "Baseline"
                       else comparison["baseline_result"]["batches"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Orders", len(orders))
    c2.metric("Total Riders", len(riders[riders["availability"] == "AVAILABLE"]))
    c3.metric("Total Batches", active_metrics["num_batches"])
    c4.metric("Total Distance (km)", f"{active_metrics['total_distance_km']:.1f}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Distance Saved (CABA vs Baseline)", f"{comparison['distance_saved_pct']:.1f}%")
    c6.metric("On-Time Delivery %", f"{active_metrics['on_time_delivery_rate']*100:.1f}%")
    c7.metric("Constraint Violations",
              sum(v for k, v in comparison[
                  ("caba_result" if algo_view != "Baseline" else "baseline_result")
              ]["violations"].items()))
    c8.metric("Avg Rider Workload (min)", f"{active_metrics['average_rider_workload_min']:.1f}")

    st.markdown("---")

    # ---------------------------------------------------------------
<<<<<<< HEAD
    # Side-by-side workflow comparison (reviewer-requested)
    # ---------------------------------------------------------------
    st.subheader("🔀 Side-by-Side Workflow Comparison")
    st.caption("Actual measured values for this scenario -- not example numbers.")
    workflow_df = _side_by_side_workflow_table(
        baseline_metrics, caba_metrics,
        comparison["baseline_result"]["batches"], comparison["caba_result"]["batches"])
    st.dataframe(workflow_df, use_container_width=True, hide_index=True)

    st.plotly_chart(visualization.plot_workload_comparison_with_threshold(
        baseline_metrics["average_rider_workload_min"],
        baseline_metrics["maximum_rider_workload_min"],
        caba_metrics["average_rider_workload_min"],
        caba_metrics["maximum_rider_workload_min"],
        config.WORKLOAD_REJECTION_THRESHOLD_MIN,
    ), use_container_width=True)

    st.markdown("---")

    # ---------------------------------------------------------------
=======
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
    # Comparison table
    # ---------------------------------------------------------------
    st.subheader("⚖️ Baseline vs CABA -- Metric Comparison")
    st.dataframe(comparison["comparison_table"], use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---------------------------------------------------------------
    # Order table
    # ---------------------------------------------------------------
    st.subheader("📦 Orders")
    orders_df = _orders_to_dataframe(orders, active_batches)
    st.dataframe(orders_df, use_container_width=True, height=300)

    st.markdown("---")

    # ---------------------------------------------------------------
    # Batch results
    # ---------------------------------------------------------------
    st.subheader("🧺 Batch Results")
    if algo_view == "Compare Both":
        tab1, tab2 = st.tabs(["Baseline Batches", "CABA Batches"])
        with tab1:
            st.dataframe(_batches_to_dataframe(comparison["baseline_result"]["batches"], orders),
                         use_container_width=True, height=300)
        with tab2:
            st.dataframe(_batches_to_dataframe(comparison["caba_result"]["batches"], orders),
                         use_container_width=True, height=300)
    else:
        st.dataframe(_batches_to_dataframe(active_batches, orders),
                     use_container_width=True, height=300)

    st.markdown("---")

    # ---------------------------------------------------------------
<<<<<<< HEAD
    # Why was this order rejected? (reviewer-requested)
    # ---------------------------------------------------------------
    st.subheader("❓ Why Was This Order Rejected?")
    rejection_df = _rejection_reasons_dataframe(comparison["caba_result"])
    if rejection_df.empty:
        st.success("No rejected orders in this scenario -- every order was assigned by CABA.")
    else:
        recovered = comparison["caba_result"].get("recovered_count", 0)
        attempted = len(comparison["caba_result"].get("recovery_log", []))
        st.caption(
            f"CABA ran a recovery pass against the full rider pool for all "
            f"{attempted} initially-unassigned orders before giving up on any of "
            f"them. {recovered} were recovered via a secondary dispatch; "
            f"{len(rejection_df)} remain genuinely infeasible for this fleet/scenario."
        )
        st.dataframe(
            rejection_df[["Order", "Result", "Reason", "Recovery Attempted"]],
            use_container_width=True, height=300, hide_index=True)
        with st.expander("Show full rejection detail text"):
            st.dataframe(rejection_df[["Order", "Full Detail"]],
                         use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---------------------------------------------------------------
=======
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
    # Visualizations
    # ---------------------------------------------------------------
    st.subheader("📈 Visualizations")

    v1, v2 = st.columns(2)
    with v1:
        st.plotly_chart(visualization.plot_delivery_locations(orders.sample(
            min(300, len(orders)), random_state=1)), use_container_width=True)
    with v2:
        st.plotly_chart(visualization.plot_distance_comparison(
            baseline_metrics["total_distance_km"], caba_metrics["total_distance_km"]),
            use_container_width=True)

    v3, v4 = st.columns(2)
    with v3:
        st.plotly_chart(visualization.plot_violation_comparison(
            comparison["baseline_result"]["violations"], comparison["caba_result"]["violations"]),
            use_container_width=True)
    with v4:
        st.plotly_chart(visualization.plot_on_time_comparison(
            baseline_metrics["on_time_delivery_rate"], caba_metrics["on_time_delivery_rate"]),
            use_container_width=True)

    v5, v6 = st.columns(2)
    with v5:
        workloads = [b.workload_minutes for b in comparison["caba_result"]["batches"]] or [0]
        st.plotly_chart(visualization.plot_workload_distribution(
            workloads, "CABA Rider Workload Distribution"), use_container_width=True)
    with v6:
        batch_sizes = [len(b.order_ids) for b in comparison["caba_result"]["batches"]] or [0]
        st.plotly_chart(visualization.plot_batch_size_distribution(
            batch_sizes, "CABA Batch Size Distribution"), use_container_width=True)

    st.markdown("---")
    st.caption(
        "Distances are computed via Haversine great-circle distance with a configurable "
        "average speed -- see src/routing.py and docs/limitations.md."
    )


if __name__ == "__main__":
    main()
