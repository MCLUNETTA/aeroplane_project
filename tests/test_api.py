import requests

from src.api import NominatimAPI, OpenSkyAPI, AeroplanesAPI
from src.base_api import BaseAPI, FlightAPI, GeoAPI, APIError


class FakeResponse:
    def __init__(self, payload=None, *, error=None, broken_json=False):
        self.payload = payload
        self.error = error
        self.broken_json = broken_json

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        if self.broken_json:
            raise ValueError("not json")
        return self.payload


def http_error(status_code):
    response = requests.Response()
    response.status_code = status_code
    return requests.HTTPError(f"HTTP {status_code}", response=response)


def test_abstract_classes_cannot_be_instantiated():
    for cls in (BaseAPI, GeoAPI, FlightAPI):
        try:
            cls()
        except TypeError:
            continue
        raise AssertionError(f"{cls.__name__} должен быть абстрактным")


def test_nominatim_returns_bounding_box(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append((url, params, headers, timeout))
        return FakeResponse(
            [{"display_name": "Spain", "boundingbox": ["36.0", "44.5", "-9.5", "3.5"]}]
        )

    monkeypatch.setattr("src.api.requests.get", fake_get)
    box = NominatimAPI(timeout=3).get_bounding_box("Spain")

    assert box == {
        "south": 36.0,
        "north": 44.5,
        "west": -9.5,
        "east": 3.5,
    }
    assert calls[0][0].endswith("/search")
    assert calls[0][1]["q"] == "Spain"
    assert "User-Agent" in calls[0][2]
    assert calls[0][3] == 3


def test_nominatim_handles_empty_and_broken_answers(monkeypatch):
    monkeypatch.setattr(
        "src.api.requests.get", lambda *a, **kw: FakeResponse([])
    )
    try:
        NominatimAPI().get_bounding_box("Nowhere")
    except ValueError as exc:
        assert "не найдена" in str(exc)
    else:
        raise AssertionError("Ожидалась ValueError")

    monkeypatch.setattr(
        "src.api.requests.get",
        lambda *a, **kw: FakeResponse([{"display_name": "Spain", "boundingbox": []}]),
    )
    try:
        NominatimAPI().get_bounding_box("Spain")
    except ValueError as exc:
        assert "boundingbox" in str(exc)
    else:
        raise AssertionError("Ожидалась ValueError")

    monkeypatch.setattr(
        "src.api.requests.get", lambda *a, **kw: FakeResponse(error=http_error(429))
    )
    try:
        NominatimAPI().get_bounding_box("Spain")
    except APIError as exc:
        assert "429" in str(exc)
    else:
        raise AssertionError("Ожидалась APIError")

    monkeypatch.setattr(
        "src.api.requests.get", lambda *a, **kw: FakeResponse(broken_json=True)
    )
    try:
        NominatimAPI()._get_json("http://example.com")
    except APIError as exc:
        assert "JSON" in str(exc)
    else:
        raise AssertionError("Ожидалась APIError")


def test_nominatim_validates_country(monkeypatch):
    def no_request(*args, **kwargs):
        raise AssertionError("Запрос не должен отправляться")

    monkeypatch.setattr("src.api.requests.get", no_request)
    for value in ("", None, 42):
        try:
            NominatimAPI().get_bounding_box(value)
        except ValueError:
            continue
        raise AssertionError(f"{value!r} должно быть отвергнуто")


def test_opensky_parses_states(monkeypatch):
    states = [
        [
            "abc123",
            "UAL1621",
            "United States",
            1700000000,
            1700000001,
            -3.5,
            40.2,
            9000.0,
            False,
            250.5,
            270.0,
            0.0,
            None,
            9100.0,
            "1234",
            False,
            0,
        ],
        [
            "def456",
            None,
            "",
            0,
            0,
            1.0,
            1.0,
            500.0,
            True,
            None,
            0,
            0,
            None,
            None,
            None,
            False,
            0,
        ],
        ["broken"],
        None,
    ]
    captured = []

    def fake_get(url, params=None, headers=None, timeout=None):
        captured.append(params)
        return FakeResponse({"time": 1700000000, "states": states})

    monkeypatch.setattr("src.api.requests.get", fake_get)
    client = OpenSkyAPI()
    result = client.get_aeroplanes(
        {"south": 36.0, "north": 44.5, "west": -9.5, "east": 3.5}
    )

    assert len(result) == 2
    assert result[0]["callsign"] == "UAL1621"
    assert result[0]["country"] == "United States"
    assert result[0]["velocity"] == 250.5
    assert result[0]["altitude"] == 9100.0
    assert result[1]["callsign"] == "UNKNOWN"
    assert result[1]["country"] == "Unknown"
    assert result[1]["altitude"] == 500.0
    assert result[1]["on_ground"] is True
    assert client.aeroplanes == result
    assert captured[0]["lamin"] == 36.0
    assert captured[0]["lomax"] == 3.5


def test_opensky_splits_area_when_crossing_meridian(monkeypatch):
    captured = []

    def fake_get(url, params=None, headers=None, timeout=None):
        captured.append(params)
        return FakeResponse({"states": []})

    monkeypatch.setattr("src.api.requests.get", fake_get)
    OpenSkyAPI().get_aeroplanes(
        {"south": 10, "north": 20, "west": 170, "east": -170}
    )

    assert len(captured) == 2
    assert (captured[0]["lomin"], captured[0]["lomax"]) == (170, 180)
    assert (captured[1]["lomin"], captured[1]["lomax"]) == (-180, -170)


def test_opensky_validates_bounding_box(monkeypatch):
    monkeypatch.setattr(
        "src.api.requests.get", lambda *a, **kw: FakeResponse({"states": []})
    )
    client = OpenSkyAPI()
    for box in (
        {},
        {"south": 10, "north": 0, "west": 0, "east": 1},
        {"south": 0, "north": 1, "west": -200, "east": 1},
        {"south": "x", "north": 1, "west": 0, "east": 1},
    ):
        try:
            client.get_aeroplanes(box)
        except ValueError:
            continue
        raise AssertionError(f"{box} должно быть отвергнуто")


def test_opensky_rejects_bad_states_payload(monkeypatch):
    monkeypatch.setattr("src.api.requests.get", lambda *a, **kw: FakeResponse({"states": "bad"}))
    try:
        OpenSkyAPI().get_aeroplanes(
            {"south": 0, "north": 1, "west": 0, "east": 1}
        )
    except APIError:
        pass
    else:
        raise AssertionError("Ожидалась APIError")

    monkeypatch.setattr("src.api.requests.get", lambda *a, **kw: FakeResponse(None))
    assert (
        OpenSkyAPI().get_aeroplanes(
            {"south": 0, "north": 1, "west": 0, "east": 1}
        )
        == []
    )


def test_facade_delegates_to_clients():
    class FakeGeo(GeoAPI):
        def _get_json(self, url, params=None):
            return []

        def get_bounding_box(self, country):
            assert country == "Spain"
            return {"south": 1, "north": 2, "west": 3, "east": 4}

    class FakeFlights(FlightAPI):
        def __init__(self):
            self.box = None

        def _get_json(self, url, params=None):
            return {}

        def get_aeroplanes(self, bounding_box):
            self.box = bounding_box
            return [{"callsign": "TEST"}]

    flights = FakeFlights()
    api = AeroplanesAPI(geocoder=FakeGeo(), flights=flights)

    assert api.get_bounding_box("Spain")["north"] == 2
    assert api.get_aeroplanes("Spain") == [{"callsign": "TEST"}]
    assert flights.box == {"south": 1, "north": 2, "west": 3, "east": 4}
    assert isinstance(AeroplanesAPI().geocoder, NominatimAPI)
    assert isinstance(AeroplanesAPI().flights, OpenSkyAPI)
