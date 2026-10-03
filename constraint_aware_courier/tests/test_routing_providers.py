"""
test_routing_providers.py
==========================
Verifies the pluggable routing-provider layer (Priority 1 enhancement):
Haversine remains the default and fully functional, OSRM is a clean,
documented stub that fails loudly rather than silently, and the factory
rejects unknown provider names.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from src import routing


def test_default_provider_is_haversine():
    provider = routing.get_routing_provider()
    assert provider.name == "haversine"


def test_haversine_distance_known_points():
    # Chennai Central (~13.0827, 80.2707) to a point ~10km east
    d = routing.haversine_distance_km(13.0827, 80.2707, 13.0827, 80.3707)
    # roughly 11 km at this latitude for 0.1 degree longitude
    assert 9.0 < d < 13.0


def test_haversine_zero_distance_for_same_point():
    d = routing.haversine_distance_km(13.0, 80.0, 13.0, 80.0)
    assert d == pytest.approx(0.0, abs=1e-9)


def test_travel_time_scales_with_delay_multiplier():
    base_time = routing.travel_time_minutes(10.0, delay_multiplier=1.0)
    delayed_time = routing.travel_time_minutes(10.0, delay_multiplier=1.75)
    assert delayed_time == pytest.approx(base_time * 1.75, rel=1e-6)


def test_osrm_provider_raises_not_implemented():
    """OSRM must fail loudly, not silently fall back to Haversine."""
    provider = routing.get_routing_provider("osrm")
    assert provider.name == "osrm"
    with pytest.raises(NotImplementedError):
        provider.distance_km(13.0, 80.0, 13.1, 80.1)
    with pytest.raises(NotImplementedError):
        provider.travel_time_minutes(5.0)


def test_unknown_provider_name_rejected():
    with pytest.raises(ValueError):
        routing.get_routing_provider("google_maps")


def test_estimate_batch_route_reports_provider_name():
    stops = [("LOC0001", 13.00, 80.25), ("LOC0002", 13.02, 80.27)]
    route = routing.estimate_batch_route(13.035, 80.27, 13.035, 80.27, stops)
    assert route["routing_provider"] == "haversine"
    assert route["total_distance_km"] > 0
    assert len(route["ordered_stop_ids"]) == 2
