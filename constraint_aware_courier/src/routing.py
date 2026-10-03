"""
routing.py
==========
<<<<<<< HEAD
Routing layer for the courier batching project.

Architecture
------------
    Coordinates
        |
        v
    Routing LAYER (this module)
        |-- HaversineRoutingProvider   (current / default -- always available)
        '-- OSRMRoutingProvider        (future / optional -- real road routing)
        |
        v
    Travel distance + estimated travel time
        |
        v
    Constraint-aware batching (src/constraints.py, src/batching_algorithm.py)

`baseline.py` and `batching_algorithm.py` never compute distance/time
themselves -- they only call the module-level functions in this file
(`haversine_distance_km`, `travel_time_minutes`, `estimate_batch_route`,
`route_stop_sequence`). Those functions delegate to whichever
`RoutingProvider` is configured via `config.ROUTING_PROVIDER`. This means
swapping Haversine for a real road-network routing engine later is a
one-file change -- no caller needs to be touched.

IMPORTANT: The default and only *implemented* provider in this prototype is
Haversine great-circle distance with a configurable average speed -- there
is no live maps / navigation API call. This is a deliberate, documented
simplification (see docs/limitations.md). `OSRMRoutingProvider` below is a
documented, runnable *interface stub* for a future enhancement, not a real
integration -- calling it raises a clear `NotImplementedError` rather than
silently falling back to Haversine, so it's obvious at runtime if it's ever
selected before being implemented.
"""

import math
from abc import ABC, abstractmethod
=======
Practical routing APPROXIMATION for the courier batching project.

IMPORTANT: This module does NOT use any live maps / navigation API. It
approximates real-world travel using Haversine great-circle distance and a
configurable average urban speed, plus fixed allowances for building access
and package handling. This is a deliberate, documented simplification
suitable for an academic prototype (see docs/limitations.md).
"""

import math
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
from typing import List, Sequence, Tuple

import config


<<<<<<< HEAD
# ---------------------------------------------------------------------------
# Routing provider interface
# ---------------------------------------------------------------------------
class RoutingProvider(ABC):
    """Common interface every routing backend must implement.

    A provider only needs to answer one question: given two points, what is
    the travel distance (km) and travel time (minutes) between them? Stop
    sequencing and batch-level aggregation (route_stop_sequence /
    estimate_batch_route, below) are implemented once, on top of this
    interface, so every provider gets them for free.
    """

    name: str = "base"

    @abstractmethod
    def distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Travel distance between two points, in kilometres."""
        raise NotImplementedError

    @abstractmethod
    def travel_time_minutes(self, distance_km: float, delay_multiplier: float = 1.0) -> float:
        """Travel time for a given distance, in minutes."""
        raise NotImplementedError


class HaversineRoutingProvider(RoutingProvider):
    """Default provider: Haversine great-circle distance + configurable
    average speed. No external calls, no network dependency, always
    available -- this is what every result in this project's reports and
    dashboard was generated with.
    """

    name = "haversine"

    def distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0088  # mean Earth radius in km
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (math.sin(dphi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    def travel_time_minutes(self, distance_km: float, delay_multiplier: float = 1.0) -> float:
        if config.AVERAGE_SPEED_KMPH <= 0:
            raise ValueError("AVERAGE_SPEED_KMPH must be positive")
        hours = distance_km / config.AVERAGE_SPEED_KMPH
        return hours * 60.0 * delay_multiplier


class OSRMRoutingProvider(RoutingProvider):
    """FUTURE / OPTIONAL enhancement hook for real road-network routing via
    a self-hosted OSRM (Open Source Routing Machine) or OpenRouteService
    instance.

    This is intentionally NOT implemented in the current prototype -- doing
    so would require a running OSRM server (`config.OSRM_BASE_URL`) and
    network access that this academic project does not assume. It is left
    here, wired into the same `RoutingProvider` interface as
    `HaversineRoutingProvider`, so that a future contributor can implement
    just the two methods below (e.g. calling OSRM's `/route/v1/driving/...`
    HTTP endpoint and parsing `distance`/`duration` from the response)
    without changing anything else in the codebase -- not `constraints.py`,
    not `batching_algorithm.py`, not `baseline.py`.

    Selecting this provider (`config.ROUTING_PROVIDER = "osrm"`) before it
    is implemented raises `NotImplementedError` immediately and loudly,
    rather than silently falling back to Haversine and producing misleading
    results.
    """

    name = "osrm"

    def distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        raise NotImplementedError(
            "OSRMRoutingProvider is a future-enhancement stub. To implement it: "
            "call f'{config.OSRM_BASE_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}' "
            "and parse the 'distance' field (metres) from the response. "
            "Until then, set config.ROUTING_PROVIDER = 'haversine'."
        )

    def travel_time_minutes(self, distance_km: float, delay_multiplier: float = 1.0) -> float:
        raise NotImplementedError(
            "OSRMRoutingProvider is a future-enhancement stub. To implement it: "
            "use the 'duration' field (seconds) from the same OSRM /route response "
            "used in distance_km(), rather than re-deriving time from distance. "
            "Until then, set config.ROUTING_PROVIDER = 'haversine'."
        )


_PROVIDERS = {
    "haversine": HaversineRoutingProvider,
    "osrm": OSRMRoutingProvider,
}


def get_routing_provider(name: str = None) -> RoutingProvider:
    """Factory: returns the configured RoutingProvider instance.

    `name` defaults to `config.ROUTING_PROVIDER` ("haversine"). Passing an
    explicit name lets tests or experiments force a specific provider
    without editing config.py.
    """
    name = (name or config.ROUTING_PROVIDER).lower()
    if name not in _PROVIDERS:
        raise ValueError(
            f"Unknown routing provider '{name}'. Available: {list(_PROVIDERS.keys())}")
    return _PROVIDERS[name]()


# Module-level default provider instance, used by the convenience functions
# below so existing callers (baseline.py, batching_algorithm.py) don't need
# to manage a provider object themselves.
_default_provider = get_routing_provider()


# ---------------------------------------------------------------------------
# Convenience functions (what baseline.py / batching_algorithm.py actually call)
# ---------------------------------------------------------------------------
def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometres.

    Named 'haversine_*' for backward compatibility / clarity in call sites
    that specifically want the Haversine formula (e.g. nearest-rider
    sorting heuristics); internally it always uses HaversineRoutingProvider
    directly, regardless of config.ROUTING_PROVIDER, since those call sites
    are approximate pre-filtering steps, not the authoritative route
    distance used for constraint checking.
    """
    return HaversineRoutingProvider().distance_km(lat1, lon1, lat2, lon2)
=======
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
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a


def travel_time_minutes(distance_km: float,
                         speed_kmph: float = config.AVERAGE_SPEED_KMPH,
                         delay_multiplier: float = 1.0) -> float:
<<<<<<< HEAD
    """Estimate travel time in minutes for a given distance, using the
    CONFIGURED routing provider (config.ROUTING_PROVIDER).

    `delay_multiplier` allows disruption scenarios (e.g. traffic/weather)
    to scale up travel time without changing the underlying distance model.
    `speed_kmph` is accepted for backward compatibility with earlier
    versions of this function but only applies when the active provider is
    Haversine-based (a road-network provider would derive time from the
    routed path instead of a flat average speed).
    """
    if _default_provider.name == "haversine" and speed_kmph != config.AVERAGE_SPEED_KMPH:
        if speed_kmph <= 0:
            raise ValueError("speed_kmph must be positive")
        hours = distance_km / speed_kmph
        return hours * 60.0 * delay_multiplier
    return _default_provider.travel_time_minutes(distance_km, delay_multiplier=delay_multiplier)
=======
    """Estimate travel time in minutes for a given distance and speed.

    `delay_multiplier` allows disruption scenarios (e.g. traffic/weather)
    to scale up travel time without changing the underlying distance model.
    """
    if speed_kmph <= 0:
        raise ValueError("speed_kmph must be positive")
    hours = distance_km / speed_kmph
    return hours * 60.0 * delay_multiplier
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a


def route_stop_sequence(start_lat: float, start_lon: float,
                         stops: Sequence[Tuple[str, float, float]]
                         ) -> List[Tuple[str, float, float]]:
    """Order a set of stops using a simple nearest-neighbour heuristic.

    `stops` is a list of (stop_id, lat, lon). This produces a practical
    (not necessarily optimal) delivery sequence, which is a standard and
    explainable approach for an academic prototype (full TSP solving is out
<<<<<<< HEAD
    of scope for a real-time batching system with dozens of riders). This
    sequencing step is provider-agnostic -- it just needs *a* distance
    function, so it uses the configured provider's distance_km().
=======
    of scope for a real-time batching system with dozens of riders).
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
    """
    remaining = list(stops)
    sequence = []
    cur_lat, cur_lon = start_lat, start_lon
    while remaining:
<<<<<<< HEAD
        distances = [_default_provider.distance_km(cur_lat, cur_lon, s[1], s[2])
                     for s in remaining]
=======
        distances = [haversine_distance_km(cur_lat, cur_lon, s[1], s[2]) for s in remaining]
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
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
<<<<<<< HEAD
    stops (deliveries), using the CONFIGURED routing provider throughout.

    Returns a dict with total_distance_km, total_travel_time_min, the
    ordered stop sequence (list of stop_ids in visiting order), and
    per-leg distances. This is the single function every batching
    algorithm calls for route estimation -- switching `config.ROUTING_PROVIDER`
    changes the numbers everywhere automatically.
    """
    provider = _default_provider

    # 1. rider travels to the pickup hub
    dist_to_hub = provider.distance_km(rider_lat, rider_lon, hub_lat, hub_lon)
=======
    stops (deliveries).

    Returns a dict with total_distance_km, total_travel_time_min, and the
    ordered stop sequence (list of stop_ids in visiting order).
    """
    # 1. rider travels to the pickup hub
    dist_to_hub = haversine_distance_km(rider_lat, rider_lon, hub_lat, hub_lon)
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a

    # 2. sequence deliveries via nearest-neighbour starting from the hub
    ordered_stops = route_stop_sequence(hub_lat, hub_lon, stops)

    total_distance = dist_to_hub
<<<<<<< HEAD
    total_time = provider.travel_time_minutes(dist_to_hub, delay_multiplier=delay_multiplier)
=======
    total_time = travel_time_minutes(dist_to_hub, delay_multiplier=delay_multiplier)
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a

    cur_lat, cur_lon = hub_lat, hub_lon
    leg_distances = []
    for stop_id, lat, lon in ordered_stops:
<<<<<<< HEAD
        d = provider.distance_km(cur_lat, cur_lon, lat, lon)
        leg_distances.append((stop_id, d))
        total_distance += d
        total_time += provider.travel_time_minutes(d, delay_multiplier=delay_multiplier)
=======
        d = haversine_distance_km(cur_lat, cur_lon, lat, lon)
        leg_distances.append((stop_id, d))
        total_distance += d
        total_time += travel_time_minutes(d, delay_multiplier=delay_multiplier)
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
        total_time += config.BUILDING_ACCESS_DELAY_MIN
        cur_lat, cur_lon = lat, lon

    return {
        "total_distance_km": total_distance,
        "total_travel_time_min": total_time,
        "ordered_stop_ids": [s[0] for s in ordered_stops],
        "leg_distances_km": leg_distances,
<<<<<<< HEAD
        "routing_provider": provider.name,
=======
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
    }
