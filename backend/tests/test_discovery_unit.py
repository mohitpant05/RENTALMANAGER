import pytest

from app.domains.resources.discovery import haversine_distance_km


def test_haversine_same_point():
    assert haversine_distance_km(30.0, 78.0, 30.0, 78.0) == 0.0


def test_haversine_known_distance():
    d = haversine_distance_km(28.6139, 77.2090, 30.0869, 78.2676)
    assert 180 < d < 200


def test_haversine_short_distance():
    d = haversine_distance_km(30.0, 78.0, 30.009, 78.0)
    assert 0.9 < d < 1.1
