"""
preprocessing.py
=================
Loading, cleaning, and type-normalising the raw orders/riders datasets
before they are fed to the baseline or CABA algorithms.
"""

import logging
from typing import Tuple

import pandas as pd

import config

logger = logging.getLogger(__name__)

DATETIME_COLUMNS_ORDERS = [
    "pickup_ready_time", "order_created_time",
    "promised_start_time", "promised_deadline",
]
DATETIME_COLUMNS_RIDERS = ["shift_start", "shift_end"]


def load_orders(path: str = config.ORDERS_FILE) -> pd.DataFrame:
    """Load and clean the orders dataset."""
    df = pd.read_csv(path)
    for col in DATETIME_COLUMNS_ORDERS:
        df[col] = pd.to_datetime(df[col])

    # basic cleaning / validation
    df["weight_kg"] = df["weight_kg"].clip(lower=0.05)
    df["volume_litre"] = df["volume_litre"].clip(lower=0.05)
    df["incompatible_group"] = df["incompatible_group"].where(
        df["incompatible_group"].notna(), None)
    df["fragile"] = df["fragile"].astype(bool)

    n_before = len(df)
    df = df.dropna(subset=["order_id", "latitude", "longitude", "promised_deadline"])
    n_after = len(df)
    if n_before != n_after:
        logger.warning("Dropped %d malformed order rows during preprocessing",
                        n_before - n_after)

    df = df.reset_index(drop=True)
    logger.info("Loaded %d orders from %s", len(df), path)
    return df


def load_riders(path: str = config.RIDERS_FILE) -> pd.DataFrame:
    """Load and clean the riders dataset."""
    df = pd.read_csv(path)
    for col in DATETIME_COLUMNS_RIDERS:
        df[col] = pd.to_datetime(df[col])

    df["capacity_kg"] = df["capacity_kg"].clip(lower=1)
    df["capacity_volume"] = df["capacity_volume"].clip(lower=1)
    df = df.dropna(subset=["rider_id"]).reset_index(drop=True)

    logger.info("Loaded %d riders from %s", len(df), path)
    return df


def load_dataset(orders_path: str = config.ORDERS_FILE,
                  riders_path: str = config.RIDERS_FILE
                  ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Convenience function to load both orders and riders together."""
    return load_orders(orders_path), load_riders(riders_path)
