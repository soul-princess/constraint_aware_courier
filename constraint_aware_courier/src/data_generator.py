"""
data_generator.py
==================
Generates realistic, reproducible synthetic data for the courier batching
project: orders.csv and riders.csv.

No real company data exists for this academic project, so distributions are
chosen to *mimic* realistic e-commerce courier operations (mixed product
types, a minority of urgent/tight-window/not-ready orders, clustered
delivery locations representing gated apartments and office complexes).
"""

import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Tuple

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)
logging.basicConfig(level=config.LOG_LEVEL, format=config.LOG_FORMAT)


def _make_buildings(rng: np.random.Generator, n: int) -> pd.DataFrame:
    """Generate a fixed set of building clusters (apartments/offices)."""
    lat = rng.uniform(*config.CITY_LAT_RANGE, size=n)
    lon = rng.uniform(*config.CITY_LON_RANGE, size=n)
    location_type = rng.choice(config.LOCATION_TYPES, size=n, p=[0.65, 0.35])
    names = []
    for i, ltype in enumerate(location_type):
        prefix = "Apt" if ltype == "Gated Apartment" else "Office"
        names.append(f"{prefix}-{i+1:03d}")
    return pd.DataFrame({
        "location_id": [f"LOC{i+1:04d}" for i in range(n)],
        "building_name": names,
        "location_type": location_type,
        "latitude": lat,
        "longitude": lon,
    })


def _incompatible_group_for(category: str, rng: np.random.Generator):
    """Assign a fine-grained incompatible group id for a subset of orders.

    This models real-world cases where two orders in the *same broad
    category* still cannot travel together (e.g. two different strong-odor
    chemical products, or two frozen items from different cold-chain
    vendors that cannot share an unrefrigerated compartment together).
    Roughly 10% of Chemical/Frozen orders receive a specific group tag.
    """
    if category in ("Chemical", "Frozen") and rng.random() < 0.10:
        return f"{category[:3].upper()}-G{rng.integers(1, 4)}"
    return None


def generate_orders(n_orders: int = config.NUM_ORDERS,
                     buildings: pd.DataFrame = None,
                     seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    """Generate a synthetic orders dataset with realistic field distributions."""
    rng = np.random.default_rng(seed)
    if buildings is None:
        buildings = _make_buildings(rng, config.NUM_BUILDINGS)

    categories = list(config.PRODUCT_CATEGORY_WEIGHTS.keys())
    weights = list(config.PRODUCT_CATEGORY_WEIGHTS.values())

    base_time = datetime(2025, 1, 6, 8, 0, 0)  # a Monday, start of operational day

    rows = []
    for i in range(n_orders):
        building = buildings.iloc[rng.integers(0, len(buildings))]
        category = rng.choice(categories, p=weights)

        # weight/volume distributions depend loosely on category
        if category == "Heavy":
            weight = rng.uniform(6.0, 15.0)
            volume = rng.uniform(15.0, 35.0)
        elif category == "Fragile":
            weight = rng.uniform(0.5, 4.0)
            volume = rng.uniform(5.0, 20.0)
        elif category == "Frozen":
            weight = rng.uniform(1.0, 6.0)
            volume = rng.uniform(4.0, 15.0)
        elif category == "Hot Food":
            weight = rng.uniform(0.5, 3.0)
            volume = rng.uniform(3.0, 10.0)
        elif category == "Chemical":
            weight = rng.uniform(1.0, 8.0)
            volume = rng.uniform(2.0, 12.0)
        else:  # Normal
            weight = rng.uniform(0.3, 5.0)
            volume = rng.uniform(2.0, 12.0)

        fragile_flag = category == "Fragile" or rng.random() < 0.05
        temp_requirement = "Frozen" if category == "Frozen" else (
            "Hot" if category == "Hot Food" else "Ambient")

        order_created_minutes = rng.integers(0, 240)  # spread orders over the morning
        order_created_time = base_time + timedelta(minutes=int(order_created_minutes))

        # pickup readiness: most orders ready shortly after creation,
        # a fraction are "not ready" for a long while (kitchen/prep delay etc.)
        if rng.random() < config.NOT_READY_ORDER_FRACTION:
            pickup_delay = rng.integers(45, 150)
        else:
            pickup_delay = rng.integers(2, 30)
        pickup_ready_time = order_created_time + timedelta(minutes=int(pickup_delay))

        # priority / urgency
        is_urgent = rng.random() < config.URGENT_ORDER_FRACTION
        priority = "URGENT" if is_urgent else rng.choice(
            ["HIGH", "NORMAL", "LOW"], p=[0.15, 0.65, 0.20])

        promised_start_time = pickup_ready_time + timedelta(minutes=int(rng.integers(5, 20)))

        # delivery window: urgent / tight-window orders get much shorter windows
        if is_urgent:
            window_minutes = rng.integers(45, 75)
        elif rng.random() < config.TIGHT_WINDOW_FRACTION:
            window_minutes = rng.integers(60, 90)
        else:
            window_minutes = rng.integers(100, 240)
        promised_deadline = promised_start_time + timedelta(minutes=int(window_minutes))

        service_time = config.DEFAULT_SERVICE_TIME_MIN + rng.uniform(-1.5, 3.0)
        service_time = max(1.5, service_time)

        incompatible_group = _incompatible_group_for(category, rng)

        rows.append({
            "order_id": f"ORD{i+1:05d}",
            "customer_id": f"CUST{rng.integers(1, n_orders // 2):05d}",
            "location_id": building["location_id"],
            "location_type": building["location_type"],
            "building_name": building["building_name"],
            "latitude": round(building["latitude"] + rng.normal(0, 0.0006), 6),
            "longitude": round(building["longitude"] + rng.normal(0, 0.0006), 6),
            "product_type": f"{category}-Item-{rng.integers(1, 50)}",
            "product_category": category,
            "weight_kg": round(float(weight), 2),
            "volume_litre": round(float(volume), 2),
            "fragile": bool(fragile_flag),
            "temperature_requirement": temp_requirement,
            "incompatible_group": incompatible_group,
            "pickup_ready_time": pickup_ready_time,
            "order_created_time": order_created_time,
            "promised_start_time": promised_start_time,
            "promised_deadline": promised_deadline,
            "priority": priority,
            "service_time_minutes": round(float(service_time), 2),
            "status": "PENDING",
        })

    df = pd.DataFrame(rows)
    logger.info("Generated %d synthetic orders", len(df))
    return df


def generate_riders(n_riders: int = config.NUM_RIDERS,
                     seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    """Generate a synthetic rider fleet."""
    rng = np.random.default_rng(seed + 1)  # different stream than orders

    base_time = datetime(2025, 1, 6, 8, 0, 0)

    rows = []
    for i in range(n_riders):
        capacity_kg = rng.integers(*config.RIDER_CAPACITY_KG_RANGE)
        capacity_volume = rng.integers(*config.RIDER_CAPACITY_VOLUME_RANGE)
        max_orders = rng.integers(*config.RIDER_MAX_ORDERS_PER_BATCH_RANGE)
        shift_start = base_time + timedelta(minutes=int(rng.integers(0, 60)))
        shift_end = shift_start + timedelta(hours=int(rng.integers(6, 9)))

        # riders start near random points around the hub (representing
        # different micro-warehouses / parking points)
        lat = config.HUB_LATITUDE + rng.normal(0, 0.02)
        lon = config.HUB_LONGITUDE + rng.normal(0, 0.02)

        rows.append({
            "rider_id": f"RID{i+1:03d}",
            "capacity_kg": int(capacity_kg),
            "capacity_volume": int(capacity_volume),
            "shift_start": shift_start,
            "shift_end": shift_end,
            "current_latitude": round(float(lat), 6),
            "current_longitude": round(float(lon), 6),
            "max_orders_per_batch": int(max_orders),
            "max_workload_minutes": config.RIDER_MAX_WORKLOAD_MINUTES,
            "availability": "AVAILABLE",
        })

    df = pd.DataFrame(rows)
    logger.info("Generated %d synthetic riders", len(df))
    return df


def generate_and_save(n_orders: int = config.NUM_ORDERS,
                       n_riders: int = config.NUM_RIDERS,
                       seed: int = config.RANDOM_SEED) -> Tuple[str, str]:
    """Generate orders + riders datasets and persist them to data/raw/."""
    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)

    rng = np.random.default_rng(seed)
    buildings = _make_buildings(rng, config.NUM_BUILDINGS)

    orders = generate_orders(n_orders, buildings=buildings, seed=seed)
    riders = generate_riders(n_riders, seed=seed)

    orders.to_csv(config.ORDERS_FILE, index=False)
    riders.to_csv(config.RIDERS_FILE, index=False)

    logger.info("Saved orders to %s", config.ORDERS_FILE)
    logger.info("Saved riders to %s", config.RIDERS_FILE)
    return config.ORDERS_FILE, config.RIDERS_FILE


if __name__ == "__main__":
    generate_and_save()
