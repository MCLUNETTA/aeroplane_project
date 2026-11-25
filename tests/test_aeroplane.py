import math

import pytest

from src.aeroplane import Aeroplane


@pytest.fixture
def slow_plane() -> Aeroplane:
    return Aeroplane("UAL1621", "United States", 210.5, 9000.0, "abc123")


@pytest.fixture
def fast_plane() -> Aeroplane:
    return Aeroplane("AIC101", "India", 268.79, 10203.18, "def456")


def test_aeroplane_stores_typed_attributes(slow_plane):
    assert slow_plane.callsign == "UAL1621"
    assert slow_plane.country == "United States"
    assert slow_plane.velocity == 210.5
    assert slow_plane.altitude == 9000.0
    assert slow_plane.icao24 == "abc123"
    assert slow_plane.on_ground is False

    annotations = Aeroplane.__annotations__
    expected = {
        "callsign": "str",
        "country": "str",
        "velocity": "float",
        "altitude": "float",
        "icao24": "str",
        "on_ground": "bool",
    }
    assert all(annotations[key] == value for key, value in expected.items())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"callsign": ""},
        {"callsign": 123},
        {"country": "   "},
        {"velocity": "fast"},
        {"velocity": -1},
        {"velocity": True},
        {"altitude": float("nan")},
        {"altitude": -10},
        {"icao24": 42},
        {"on_ground": 1},
    ],
)
def test_aeroplane_validates_data(slow_plane, kwargs):
    payload = slow_plane.to_dict()
    payload.update(kwargs)
    with pytest.raises(ValueError):
        Aeroplane(**payload)


def test_comparison_by_velocity_and_altitude(slow_plane, fast_plane):
    assert fast_plane.compare_by_velocity(slow_plane) == 1
    assert slow_plane.compare_by_velocity(fast_plane) == -1
    assert slow_plane.compare_by_velocity(
        Aeroplane("X", "Spain", 210.5, 100)
    ) == 0

    assert fast_plane.compare_by_altitude(slow_plane) == 1
    assert slow_plane.compare_by_altitude(fast_plane) == -1
    assert fast_plane.is_faster_than(slow_plane) is True
    assert fast_plane.is_higher_than(slow_plane) is True
    assert slow_plane.is_higher_than(fast_plane) is False


def test_ordering_uses_altitude(slow_plane, fast_plane):
    assert fast_plane > slow_plane
    assert slow_plane < fast_plane
    assert sorted([fast_plane, slow_plane]) == [slow_plane, fast_plane]


def test_comparison_with_other_type_raises(slow_plane):
    with pytest.raises(TypeError):
        slow_plane.compare_by_altitude("another plane")
    with pytest.raises(TypeError):
        slow_plane.compare_by_velocity(None)
    assert slow_plane.__lt__("another plane") is NotImplemented
    assert slow_plane.__gt__(5) is NotImplemented


def test_cast_to_object_list_accepts_dicts_aliases_and_objects(slow_plane):
    data = [
        {
            "callsign": " AFR123 ",
            "origin_country": "France",
            "velocity": 250,
            "geo_altitude": 11000,
            "icao24": "ff0001",
            "on_ground": False,
            "extra_field": "ignored",
        },
        {
            "callsign": "BAW456",
            "country": "United Kingdom",
            "speed": 200,
            "baro_altitude": 8000,
        },
        slow_plane,
    ]

    result = Aeroplane.cast_to_object_list(data)

    assert len(result) == 3
    assert result[0].callsign == "AFR123"
    assert result[0].country == "France"
    assert result[0].altitude == 11000.0
    assert result[1].country == "United Kingdom"
    assert result[2] is slow_plane


@pytest.mark.parametrize("data", [None, "not a list", {"callsign": "X"}, [123]])
def test_cast_to_object_list_rejects_bad_input(data):
    with pytest.raises((TypeError, ValueError)):
        Aeroplane.cast_to_object_list(data)


def test_cast_to_object_list_rejects_invalid_fields():
    with pytest.raises(ValueError, match="Неверные данные самолёта #0"):
        Aeroplane.cast_to_object_list([{"callsign": "X", "country": ""}])


def test_to_dict_and_str(slow_plane):
    assert slow_plane.to_dict()["callsign"] == "UAL1621"
    assert "UAL1621" in str(slow_plane)
    assert "9000" in str(slow_plane)


def test_optional_values_are_normalized(slow_plane):
    plane = Aeroplane("X", "Spain", 100, 0, None, False)  # type: ignore[arg-type]
    assert plane.icao24 == ""
    assert math.isfinite(plane.altitude)
