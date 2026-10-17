import pytest

from app.services.geofence import distance_meters


def test_same_coordinate_has_zero_distance():
    assert distance_meters(13.165771, 77.558813, 13.165771, 77.558813) == pytest.approx(0)


def test_distance_is_symmetric():
    forward = distance_meters(13.165771, 77.558813, 13.169332, 77.559002)
    reverse = distance_meters(13.169332, 77.559002, 13.165771, 77.558813)

    assert forward == pytest.approx(reverse)


def test_distance_between_distinct_points_is_positive():
    distance = distance_meters(13.165771, 77.558813, 13.169332, 77.559002)

    assert distance > 0
