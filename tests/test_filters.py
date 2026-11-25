import pytest

from src.aeroplane import Aeroplane
from src.filters import (
    filter_aeroplanes,
    get_aeroplanes_by_altitude,
    get_top_aeroplanes,
    parse_altitude_range,
    print_aeroplanes,
    sort_aeroplanes,
)


@pytest.fixture
def planes() -> list[Aeroplane]:
    return [
        Aeroplane("LOW1", "Spain", 200.0, 8000.0),
        Aeroplane("HIGH1", "United States", 300.0, 12000.0),
        Aeroplane("HIGH2", "France", 250.0, 11000.0),
        Aeroplane("USA1", "США", 150.0, 9000.0),
    ]


def test_filter_by_country_is_case_insensitive(planes):
    assert [p.callsign for p in filter_aeroplanes(planes, "spain")] == ["LOW1"]
    assert [p.callsign for p in filter_aeroplanes(planes, ["united", "france"])] == [
        "HIGH1",
        "HIGH2",
    ]
    assert [p.callsign for p in filter_aeroplanes(planes, "сша")] == ["HIGH1", "USA1"]
    assert filter_aeroplanes(planes, []) == planes
    assert filter_aeroplanes(planes, None) == planes


def test_filter_accepts_dicts_and_rejects_bad_input(planes):
    data = [plane.to_dict() for plane in planes]
    assert [p.callsign for p in filter_aeroplanes(data, "Spain")] == ["LOW1"]
    with pytest.raises(TypeError):
        filter_aeroplanes(planes, 123)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("100000 - 150000", (100000.0, 150000.0)),
        ("8000-12000", (8000.0, 12000.0)),
        ("1 до 2", (1.0, 2.0)),
        ("1 to 2", (1.0, 2.0)),
        ("", (float("-inf"), float("inf"))),
        (None, (float("-inf"), float("inf"))),
        ((100, 200), (100.0, 200.0)),
    ],
)
def test_parse_altitude_range(value, expected):
    assert parse_altitude_range(value) == expected


@pytest.mark.parametrize("value", ["abc", "200 - 100", (1,), 42, ("x", 2)])
def test_parse_altitude_range_rejects_bad_values(value):
    with pytest.raises(ValueError):
        parse_altitude_range(value)


def test_get_aeroplanes_by_altitude(planes):
    result = get_aeroplanes_by_altitude(planes, "9000 - 12000")
    assert [p.callsign for p in result] == ["HIGH1", "HIGH2", "USA1"]

    assert get_aeroplanes_by_altitude(planes, "") == planes
    with pytest.raises(ValueError):
        get_aeroplanes_by_altitude(planes, "wrong")


def test_sort_desc_by_altitude_and_custom_field(planes):
    assert [p.callsign for p in sort_aeroplanes(planes)] == [
        "HIGH1",
        "HIGH2",
        "USA1",
        "LOW1",
    ]
    assert [p.callsign for p in sort_aeroplanes(planes, by="velocity")] == [
        "HIGH1",
        "HIGH2",
        "LOW1",
        "USA1",
    ]
    assert [p.callsign for p in sort_aeroplanes(planes, reverse=False)] == [
        "LOW1",
        "USA1",
        "HIGH2",
        "HIGH1",
    ]

    with pytest.raises(ValueError):
        sort_aeroplanes(planes, by="missing")
    with pytest.raises(TypeError):
        sort_aeroplanes(planes, reverse="yes")


def test_top_n_is_desc_and_validated(planes):
    assert [p.callsign for p in get_top_aeroplanes(planes, 2)] == ["HIGH1", "HIGH2"]
    assert len(get_top_aeroplanes(planes, 10)) == 4

    for bad_n in (0, -1, "3", True, 2.5):
        with pytest.raises(ValueError):
            get_top_aeroplanes(planes, bad_n)


def test_print_aeroplanes(capsys, planes):
    print_aeroplanes(get_top_aeroplanes(planes, 2))
    output = capsys.readouterr().out
    assert "HIGH1" in output
    assert "Высота, м" in output
    assert output.index("HIGH1") < output.index("HIGH2")

    print_aeroplanes([])
    assert "Самолёты не найдены." in capsys.readouterr().out
