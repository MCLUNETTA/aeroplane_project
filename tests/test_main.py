import builtins

import pytest

from src.api import APIError
from src.main import _read_top_n, user_interaction


class FakeAPI:
    def __init__(self, data=None, error=None):
        self.data = data or []
        self.error = error
        self.requests = []

    def get_aeroplanes(self, country):
        self.requests.append(country)
        if self.error:
            raise self.error
        return self.data


class FakeSaver:
    def __init__(self, error=None):
        self.file_path = "fake.json"
        self.saved = []
        self.error = error

    def add_aeroplane(self, aeroplane):
        if self.error:
            raise self.error
        self.saved.append(aeroplane)


def feed(monkeypatch, *answers):
    iterator = iter(answers)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(iterator))


def sample_data():
    return [
        {
            "callsign": "LOW1",
            "country": "Spain",
            "velocity": 200.0,
            "altitude": 8000.0,
            "icao24": "aaa",
        },
        {
            "callsign": "HIGH1",
            "country": "United States",
            "velocity": 300.0,
            "altitude": 12000.0,
            "icao24": "bbb",
        },
        {
            "callsign": "HIGH2",
            "country": "France",
            "velocity": 250.0,
            "altitude": 11000.0,
            "icao24": "ccc",
        },
    ]


def test_user_interaction_full_flow(monkeypatch, capsys):
    api = FakeAPI(sample_data())
    saver = FakeSaver()
    feed(monkeypatch, "Spain", "2", "United States France", "9000 - 12000")

    result = user_interaction(api=api, saver=saver)
    output = capsys.readouterr().out

    assert [plane.callsign for plane in result] == ["HIGH1", "HIGH2"]
    assert api.requests == ["Spain"]
    assert len(saver.saved) == 3
    assert "Топ-2" in output
    assert "fake.json" in output
    assert output.index("HIGH1") < output.index("HIGH2")


def test_user_interaction_without_filters(monkeypatch, capsys):
    api = FakeAPI(sample_data())
    saver = FakeSaver()
    feed(monkeypatch, "Spain", "1", "", "")

    result = user_interaction(api=api, saver=saver)

    assert [plane.callsign for plane in result] == ["HIGH1"]
    assert "Топ-1" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("answers", "message", "expected_requests"),
    [
        (("", "2", "", ""), "Название страны", []),
        (("Spain", "abc", "", ""), "целым числом", []),
        (("Spain", "0", "", ""), "больше нуля", []),
        (("Spain", "2", "", "wrong range"), "диапазон", ["Spain"]),
    ],
)
def test_user_interaction_handles_bad_input(
    monkeypatch, capsys, answers, message, expected_requests
):
    api = FakeAPI(sample_data())
    feed(monkeypatch, *answers)

    result = user_interaction(api=api, saver=FakeSaver())

    assert result == []
    assert message in capsys.readouterr().out
    assert api.requests == expected_requests


def test_user_interaction_handles_api_and_storage_errors(monkeypatch, capsys):
    api = FakeAPI(error=APIError("сервис недоступен"))
    feed(monkeypatch, "Spain", "1", "", "")
    assert user_interaction(api=api, saver=FakeSaver()) == []
    assert "сервис недоступен" in capsys.readouterr().out

    api = FakeAPI(sample_data())
    feed(monkeypatch, "Spain", "1", "", "")
    assert user_interaction(api=api, saver=FakeSaver(error=RuntimeError("disk full"))) == []
    assert "disk full" in capsys.readouterr().out


def test_user_interaction_handles_eof(monkeypatch, capsys):
    monkeypatch.setattr(builtins, "input", lambda prompt="": (_ for _ in ()).throw(EOFError))
    assert user_interaction(api=FakeAPI(), saver=FakeSaver()) == []
    assert "Ввод прерван" in capsys.readouterr().out


def test_read_top_n():
    assert _read_top_n(" 3 ") == 3
    for value in ("x", "0", "-2"):
        with pytest.raises(ValueError):
            _read_top_n(value)
