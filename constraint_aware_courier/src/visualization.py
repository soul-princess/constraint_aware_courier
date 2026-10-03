"""
visualization.py
=================
Reusable chart builders (Plotly for interactivity in Streamlit, Matplotlib
for static report figures) used across app.py and the experiment scripts.
"""

from typing import Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def plot_delivery_locations(orders: pd.DataFrame) -> go.Figure:
    """Scatter map of delivery locations coloured by product category."""
    fig = px.scatter_map(
        orders, lat="latitude", lon="longitude", color="product_category",
        hover_data=["order_id", "building_name", "priority"],
        zoom=10, height=500, map_style="open-street-map",
        title="Delivery Locations by Product Category",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    return fig


def plot_distance_comparison(baseline_km: float, caba_km: float) -> go.Figure:
    fig = go.Figure(data=[
        go.Bar(name="Total Distance (km)", x=["Baseline", "CABA"],
               y=[baseline_km, caba_km],
               marker_color=["#d62728", "#2ca02c"])
    ])
    fig.update_layout(title="Baseline vs CABA: Total Distance", yaxis_title="Distance (km)")
    return fig


def plot_violation_comparison(baseline_violations: dict, caba_violations: dict) -> go.Figure:
    categories = list(baseline_violations.keys())
    fig = go.Figure(data=[
        go.Bar(name="Baseline", x=categories, y=[baseline_violations[c] for c in categories],
               marker_color="#d62728"),
        go.Bar(name="CABA", x=categories, y=[caba_violations[c] for c in categories],
               marker_color="#2ca02c"),
    ])
    fig.update_layout(barmode="group", title="Constraint Violations: Baseline vs CABA",
                       yaxis_title="Violation Count")
    return fig


def plot_workload_distribution(workloads: List[float], title: str) -> go.Figure:
    fig = px.histogram(x=workloads, nbins=20, title=title,
                        labels={"x": "Rider Workload (minutes)"})
    return fig


def plot_batch_size_distribution(batch_sizes: List[int], title: str) -> go.Figure:
    fig = px.histogram(x=batch_sizes, nbins=15, title=title,
                        labels={"x": "Batch Size (orders per batch)"})
    return fig


def plot_scenario_comparison(scenario_metrics: Dict[str, dict], metric_key: str,
                              metric_label: str) -> go.Figure:
    """Compare a metric across multiple scenarios for both algorithms."""
    scenarios = list(scenario_metrics.keys())
    baseline_vals = [scenario_metrics[s]["baseline"][metric_key] for s in scenarios]
    caba_vals = [scenario_metrics[s]["caba"][metric_key] for s in scenarios]

    fig = go.Figure(data=[
        go.Bar(name="Baseline", x=scenarios, y=baseline_vals, marker_color="#d62728"),
        go.Bar(name="CABA", x=scenarios, y=caba_vals, marker_color="#2ca02c"),
    ])
    fig.update_layout(barmode="group", title=f"{metric_label}: Normal vs Disruption Scenarios",
                       yaxis_title=metric_label)
    return fig


def plot_workload_comparison_with_threshold(baseline_avg: float, baseline_max: float,
                                             caba_avg: float, caba_max: float,
                                             max_allowed: float) -> go.Figure:
    """Side-by-side rider workload comparison (average + maximum per
    algorithm) with a horizontal reference line for the operational
    'maximum allowed' workload threshold -- directly answers "did this
    optimization dump extra burden on the rider?" at a glance.
    """
    fig = go.Figure(data=[
        go.Bar(name="Average Workload", x=["Baseline", "CABA"],
               y=[baseline_avg, caba_avg], marker_color="#1f77b4"),
        go.Bar(name="Maximum Workload", x=["Baseline", "CABA"],
               y=[baseline_max, caba_max], marker_color="#d62728"),
    ])
    fig.add_hline(y=max_allowed, line_dash="dash", line_color="black",
                   annotation_text=f"Maximum Allowed ({max_allowed:.0f} min)",
                   annotation_position="top left")
    fig.update_layout(barmode="group", title="Rider Workload Comparison: Baseline vs CABA",
                       yaxis_title="Workload (minutes)")
    return fig


def plot_on_time_comparison(baseline_rate: float, caba_rate: float) -> go.Figure:
    fig = go.Figure(data=[
        go.Bar(name="On-Time Delivery Rate", x=["Baseline", "CABA"],
               y=[baseline_rate * 100, caba_rate * 100],
               marker_color=["#d62728", "#2ca02c"])
    ])
    fig.update_layout(title="On-Time Delivery Rate Comparison", yaxis_title="% On Time",
                       yaxis_range=[0, 100])
    return fig
