# -*- coding: utf-8 -*-
"""
test_routing.py - Unit test suite for spatial routing and Nearest Neighbor TSP
"""
import pytest
from backend.main import haversine_distance, solve_tsp_nearest_neighbor

def test_haversine_accuracy():
    # Chùa Bà Thiên Hậu to Hội Quán Nghĩa An ~ 0.15 km
    d = haversine_distance(10.75338, 106.65997, 10.75389, 106.66120)
    assert 0.1 <= d <= 0.3, "Distance calculation between adjacent temples is inaccurate"

def test_nearest_neighbor_ordering():
    start = {"lat": 10.7500, "lon": 106.6500}
    places = [
        {"id": 1, "name": "Far Place", "lat": 10.7900, "lon": 106.7000},
        {"id": 2, "name": "Near Place", "lat": 10.7510, "lon": 106.6510},
        {"id": 3, "name": "Medium Place", "lat": 10.7600, "lon": 106.6600}
    ]
    route = solve_tsp_nearest_neighbor(start, places)
    assert len(route) == 3
    # Near Place must be visited first
    assert route[0]["id"] == 2
    # Medium Place next
    assert route[1]["id"] == 3
    # Far Place last
    assert route[2]["id"] == 1
