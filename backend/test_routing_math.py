# -*- coding: utf-8 -*-
import math
from backend.main import haversine_distance

def test_haversine():
    # Chùa Bà Thiên Hậu: 10.75338, 106.65997
    # Chợ Bình Tây: 10.74853, 106.65175
    # Khoảng cách thực tế ~ 1.05 km
    dist = haversine_distance(10.75338, 106.65997, 10.74853, 106.65175)
    print(f"Distance Thien Hau -> Binh Tay: {dist} km")
    assert 0.9 <= dist <= 1.2, "Haversine calculation out of expected range!"

    # Test identical point distance should be 0.0
    zero_dist = haversine_distance(10.755, 106.66, 10.755, 106.66)
    assert zero_dist == 0.0, "Identical points should yield 0.0 km"
    print("[PASS] All Haversine distance unit tests passed successfully.")

if __name__ == "__main__":
    test_haversine()
