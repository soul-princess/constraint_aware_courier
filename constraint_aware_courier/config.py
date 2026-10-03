"""
config.py
=========
Central configuration for the Constraint-Aware Courier Batching project.
All tunable parameters live here so no file has hard-coded magic numbers.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
SCENARIO_DATA_DIR = os.path.join(DATA_DIR, "scenarios")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

ORDERS_FILE = os.path.join(RAW_DATA_DIR, "orders.csv")
RIDERS_FILE = os.path.join(RAW_DATA_DIR, "riders.csv")

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Dataset generation parameters
# ---------------------------------------------------------------------------
NUM_ORDERS = 1000
NUM_RIDERS = 55
NUM_BUILDINGS = 40  # gated apartments + office complexes combined

# City bounding box (synthetic city, ~ realistic sized metro area, in degrees)
# Sized so the hub-to-delivery travel distance/time is realistic relative to
# promised delivery windows (a courier hub typically serves an ~8-10km radius
# service zone, not an entire sprawling metro).
CITY_LAT_RANGE = (12.99, 13.08)   # roughly a 10km x 10km zone around the hub
CITY_LON_RANGE = (80.22, 80.32)

# Hub / warehouse location (single pickup source for simplicity, can be
# generalized to multiple pickup hubs since 'pickup_ready_time' already
# models per-order readiness independent of hub count)
HUB_LATITUDE = 13.035
HUB_LONGITUDE = 80.27

PRODUCT_CATEGORIES = ["Normal", "Fragile", "Heavy", "Frozen", "Hot Food", "Chemical"]
LOCATION_TYPES = ["Gated Apartment", "Office Complex"]

# Proportion of each product category (must sum to 1.0)
PRODUCT_CATEGORY_WEIGHTS = {
    "Normal": 0.45,
    "Fragile": 0.15,
    "Heavy": 0.10,
    "Frozen": 0.10,
    "Hot Food": 0.12,
    "Chemical": 0.08,
}

URGENT_ORDER_FRACTION = 0.12
NOT_READY_ORDER_FRACTION = 0.15
TIGHT_WINDOW_FRACTION = 0.20

# ---------------------------------------------------------------------------
# Routing / travel time approximation
# ---------------------------------------------------------------------------
AVERAGE_SPEED_KMPH = 26.0          # average urban delivery vehicle speed
BUILDING_ACCESS_DELAY_MIN = 5.0    # avg minutes lost per building (security/lift)
DEFAULT_SERVICE_TIME_MIN = 3.5     # avg minutes to hand over a package

# Which routing provider src/routing.py should use for distance/time
# calculations. "haversine" is the default and the only one implemented in
# this prototype. "osrm" is a documented future-enhancement hook (see
# src/routing.py -> OSRMRoutingProvider) for swapping in real road-network
# routing (e.g. a self-hosted OSRM or OpenRouteService instance) without
# changing any caller (baseline.py / batching_algorithm.py never call
# distance/time math directly -- they always go through routing.py).
ROUTING_PROVIDER = "haversine"
OSRM_BASE_URL = None  # e.g. "http://localhost:5000" if/when OSRM is wired up

# ---------------------------------------------------------------------------
# Rider parameters
# ---------------------------------------------------------------------------
RIDER_CAPACITY_KG_RANGE = (15, 30)
RIDER_CAPACITY_VOLUME_RANGE = (40, 80)   # litres
RIDER_MAX_ORDERS_PER_BATCH_RANGE = (4, 9)
RIDER_MAX_WORKLOAD_MINUTES = 240          # 4-hour operational shift cap per batch cycle

# ---------------------------------------------------------------------------
# CABA constraint thresholds
# ---------------------------------------------------------------------------
MAX_STOPS_PER_BATCH = 6                 # max distinct buildings per batch
MAX_WAITING_TIME_MIN = 15.0             # max minutes a rider may wait for pickup readiness
DEADLINE_SAFETY_BUFFER_MIN = 5.0        # safety margin before promised deadline

# Workload score thresholds (minutes) -> classification bands
WORKLOAD_BANDS = {
    "LOW": (0, 90),
    "MEDIUM": (90, 150),
    "HIGH": (150, 210),
    "EXCESSIVE": (210, float("inf")),
}
WORKLOAD_REJECTION_THRESHOLD_MIN = 210.0  # batches with workload >= this are rejected

# ---------------------------------------------------------------------------
# Objective function weights (used to compute Batch Score; lower is better)
# ---------------------------------------------------------------------------
WEIGHT_DISTANCE = 1.0
WEIGHT_DEADLINE_RISK = 4.0
WEIGHT_WORKLOAD = 2.0
WEIGHT_WAITING_TIME = 1.5
WEIGHT_INCOMPATIBILITY = 1e6   # effectively a hard constraint
WEIGHT_CAPACITY = 1e6          # effectively a hard constraint
URGENT_PRIORITY_BONUS = 25.0   # score reduction (bonus) for batches carrying urgent orders

# ---------------------------------------------------------------------------
# Disruption scenario parameters
# ---------------------------------------------------------------------------
DISRUPTION_RIDER_LOSS_FRACTION = 0.25      # Scenario A: remove 25% of riders
DISRUPTION_TRAVEL_DELAY_MULTIPLIER = 1.75  # Scenario B: +75% travel time
DISRUPTION_URGENT_SURGE_FRACTION = 0.15    # Scenario C: 15% extra orders become urgent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
