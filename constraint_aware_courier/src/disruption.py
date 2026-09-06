"""
disruption.py
==============
Prepares disrupted operating-day scenarios so both the baseline and CABA
can be re-run against realistic operational disruptions (Constraint 8 /
Section 11 of the spec).

Three scenarios are implemented:
  A. Rider capacity loss  -- a fraction of riders become unavailable.
  B. Travel delay          -- travel time is scaled up (traffic/weather).
  C. Urgent demand surge   -- a fraction of orders become urgent with a
                               tighter deadline.
"""

import logging
from typing import Tuple

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)


def scenario_rider_capacity_loss(riders: pd.DataFrame,
                                  fraction: float = config.DISRUPTION_RIDER_LOSS_FRACTION,
                                  seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    """Scenario A: mark a random fraction of riders as UNAVAILABLE."""
    rng = np.random.default_rng(seed + 100)
    riders = riders.copy()
    n_remove = max(1, int(len(riders) * fraction))
    removed_idx = rng.choice(riders.index, size=n_remove, replace=False)
    riders.loc[removed_idx, "availability"] = "UNAVAILABLE"
    logger.info("Scenario A: %d/%d riders marked UNAVAILABLE", n_remove, len(riders))
    return riders


def scenario_travel_delay(multiplier: float = config.DISRUPTION_TRAVEL_DELAY_MULTIPLIER
                           ) -> float:
    """Scenario B: return the delay multiplier to be applied to travel time
    estimates throughout routing. Kept as a simple function (rather than
    mutating data) because travel delay affects a *calculation*, not a
    dataset field."""
    logger.info("Scenario B: travel time multiplier set to %.2f", multiplier)
    return multiplier


def scenario_urgent_demand_surge(orders: pd.DataFrame,
                                  fraction: float = config.DISRUPTION_URGENT_SURGE_FRACTION,
                                  seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    """Scenario C: convert a fraction of non-urgent orders to URGENT with a
    tightened promised_deadline."""
    rng = np.random.default_rng(seed + 200)
    orders = orders.copy()
    eligible = orders[orders["priority"] != "URGENT"].index
    n_surge = max(1, int(len(orders) * fraction))
    n_surge = min(n_surge, len(eligible))
    surge_idx = rng.choice(eligible, size=n_surge, replace=False)

    orders.loc[surge_idx, "priority"] = "URGENT"
    # tighten deadline to promised_start_time + 30-45 minutes
    tightened_minutes = rng.integers(30, 45, size=n_surge)
    new_deadlines = orders.loc[surge_idx, "promised_start_time"] + pd.to_timedelta(
        tightened_minutes, unit="m")
    # never loosen an already-tighter deadline
    orders.loc[surge_idx, "promised_deadline"] = np.minimum(
        orders.loc[surge_idx, "promised_deadline"], new_deadlines)

    logger.info("Scenario C: %d orders converted to URGENT with tightened deadlines", n_surge)
    return orders


def apply_scenario(scenario_name: str, orders: pd.DataFrame, riders: pd.DataFrame,
                    seed: int = config.RANDOM_SEED) -> Tuple[pd.DataFrame, pd.DataFrame, float]:
    """Apply a named scenario and return (orders, riders, delay_multiplier).

    scenario_name in {"normal", "rider_loss", "travel_delay", "urgent_surge"}
    """
    delay_multiplier = 1.0
    if scenario_name == "normal":
        pass
    elif scenario_name == "rider_loss":
        riders = scenario_rider_capacity_loss(riders, seed=seed)
    elif scenario_name == "travel_delay":
        delay_multiplier = scenario_travel_delay()
    elif scenario_name == "urgent_surge":
        orders = scenario_urgent_demand_surge(orders, seed=seed)
    else:
        raise ValueError(f"Unknown scenario: {scenario_name}")

    return orders, riders, delay_multiplier
