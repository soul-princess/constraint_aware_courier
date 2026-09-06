"""
routing.py
==========
Practical routing APPROXIMATION for the courier batching project.

IMPORTANT: This module does NOT use any live maps / navigation API. It
approximates real-world travel using Haversine great-circle distance and a
configurable average urban speed, plus fixed allowances for building access
and package handling. This is a deliberate, documented simplification
suitable for an academic prototype (see docs/limitations.md).
"""

import math
from typing import List, Sequence, Tuple

import config


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    r = 6371.0088  # mean Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def travel_time_minutes(distance_km: float,
                         speed_kmph: float = config.AVERAGE_SPEED_KMPH,
                         delay_multiplier: float = 1.0) -> float:
    """Estimate travel time in minutes for a given distance and speed.

    `delay_multiplier` allows disruption scenarios (e.g. traffic/weather)
    to scale up travel time without changing the underlying distance model.
    """
    if speed_kmph <= 0:
        raise ValueError("speed_kmph must be positive")
    hours = distance_km / speed_kmph
    return hours * 60.0 * delay_multiplier


def route_stop_sequence(start_lat: float, start_lon: float,
                         stops: Sequence[Tuple[str, float, float]]
                         ) -> List[Tuple[str, float, float]]:
    """Order a set of stops using a simple nearest-neighbour heuristic.

    `stops` is a list of (stop_id, lat, lon). This produces a practical
    (not necessarily optimal) delivery sequence, which is a standard and
    explainable approach for an academic prototype (full TSP solving is out
    of scope for a real-time batching system with dozens of riders).
    """
    remaining = list(stops)
    sequence = []
    cur_lat, cur_lon = start_lat, start_lon
    while remaining:
        distances = [haversine_distance_km(cur_lat, cur_lon, s[1], s[2]) for s in remaining]
        nearest_idx = distances.index(min(distances))
        nearest = remaining.pop(nearest_idx)
        sequence.append(nearest)
        cur_lat, cur_lon = nearest[1], nearest[2]
    return sequence


def estimate_batch_route(rider_lat: float, rider_lon: float,
                          hub_lat: float, hub_lon: float,
                          stops: Sequence[Tuple[str, float, float]],
                          delay_multiplier: float = 1.0
                          ) -> dict:
    """Estimate total distance/time for: rider -> hub (pickup) -> sequenced
    stops (deliveries).

    Returns a dict with total_distance_km, total_travel_time_min, and the
    ordered stop sequence (list of stop_ids in visiting order).
    """
    # 1. rider travels to the pickup hub
    dist_to_hub = haversine_distance_km(rider_lat, rider_lon, hub_lat, hub_lon)

    # 2. sequence deliveries via nearest-neighbour starting from the hub
    ordered_stops = route_stop_sequence(hub_lat, hub_lon, stops)

    total_distance = dist_to_hub
    total_time = travel_time_minutes(dist_to_hub, delay_multiplier=delay_multiplier)

    cur_lat, cur_lon = hub_lat, hub_lon
    leg_distances = []
    for stop_id, lat, lon in ordered_stops:
        d = haversine_distance_km(cur_lat, cur_lon, lat, lon)
        leg_distances.append((stop_id, d))
        total_distance += d
        total_time += travel_time_minutes(d, delay_multiplier=delay_multiplier)
        total_time += config.BUILDING_ACCESS_DELAY_MIN
        cur_lat, cur_lon = lat, lon

    return {
        "total_distance_km": total_distance,
        "total_travel_time_min": total_time,
        "ordered_stop_ids": [s[0] for s in ordered_stops],
        "leg_distances_km": leg_distances,
    }
