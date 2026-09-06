"""
run_experiments.py
==================
Executes the REAL experiments required by the project spec:
  1. Normal-day experiment (baseline vs CABA)
  2. Three disruption scenarios (rider capacity loss, travel delay,
     urgent demand surge), each run against baseline vs CABA

All numbers in reports/experiment_results.csv are ACTUALLY MEASURED by
running the algorithms against the same synthetic dataset -- nothing here
is fabricated.

Usage:
    python run_experiments.py
"""

import logging
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from src import preprocessing, disruption, evaluation

logging.basicConfig(level=config.LOG_LEVEL, format=config.LOG_FORMAT)
logger = logging.getLogger(__name__)

SCENARIOS = ["normal", "rider_loss", "travel_delay", "urgent_surge"]
SCENARIO_LABELS = {
    "normal": "Normal Day",
    "rider_loss": "Disruption A: Rider Capacity Loss",
    "travel_delay": "Disruption B: Travel Delay",
    "urgent_surge": "Disruption C: Urgent Demand Surge",
}


def main():
    os.makedirs(config.REPORTS_DIR, exist_ok=True)

    orders_raw, riders_raw = preprocessing.load_dataset()
    logger.info("Loaded base dataset: %d orders, %d riders", len(orders_raw), len(riders_raw))

    all_rows = []
    failure_rows = []

    for scenario in SCENARIOS:
        logger.info("=" * 70)
        logger.info("Running scenario: %s", SCENARIO_LABELS[scenario])

        orders, riders, delay_multiplier = disruption.apply_scenario(
            scenario, orders_raw, riders_raw)

        comparison = evaluation.compare_algorithms(orders, riders, delay_multiplier)

        for _, row in comparison["comparison_table"].iterrows():
            all_rows.append({
                "Scenario": SCENARIO_LABELS[scenario],
                "Metric": row["Metric"],
                "Baseline": row["Baseline"],
                "CABA": row["CABA"],
                "Improvement (%)": row["Improvement (%)"],
            })

        all_rows.append({
            "Scenario": SCENARIO_LABELS[scenario],
            "Metric": "Distance Saved (km)",
            "Baseline": "-",
            "CABA": round(comparison["distance_saved_km"], 2),
            "Improvement (%)": "-",
        })
        all_rows.append({
            "Scenario": SCENARIO_LABELS[scenario],
            "Metric": "Distance Saved (%)",
            "Baseline": "-",
            "CABA": round(comparison["distance_saved_pct"], 2),
            "Improvement (%)": "-",
        })

        # failure analysis rows: unassigned orders and their reasons (CABA)
        caba_result = comparison["caba_result"]
        for reason_row in caba_result.get("unassigned_reasons", [])[:200]:
            failure_rows.append({
                "Scenario": SCENARIO_LABELS[scenario],
                "Algorithm": "CABA",
                "order_id": reason_row["order_id"],
                "reason": reason_row["reason"],
            })

        logger.info("%s -- CABA distance saved: %.2f km (%.1f%%)",
                    SCENARIO_LABELS[scenario], comparison["distance_saved_km"],
                    comparison["distance_saved_pct"])

    results_df = pd.DataFrame(all_rows)
    results_path = os.path.join(config.REPORTS_DIR, "experiment_results.csv")
    results_df.to_csv(results_path, index=False)
    logger.info("Saved experiment results to %s", results_path)

    failure_df = pd.DataFrame(failure_rows)
    failure_path = os.path.join(config.REPORTS_DIR, "failure_analysis.csv")
    failure_df.to_csv(failure_path, index=False)
    logger.info("Saved failure analysis to %s", failure_path)

    print("\n" + "=" * 70)
    print("EXPERIMENT COMPLETE")
    print("=" * 70)
    print(results_df.to_string(index=False))


if __name__ == "__main__":
    main()
