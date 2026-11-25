"""Клиенты для nominatim.openstreetmap.org и opensky-network.org."""

from __future__ import annotations

from typing import Any

import requests

from src.base_api import APIError, BaseAPI, FlightAPI, GeoAPI

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPENSKY_URL = "https://opensky-network.org/api/states/all"
USER_AGENT = "aircraft-tracker-coursework/1.0 (educational project)"


def _fetch_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> Any:
    """Выполнить GET-запрос, проверить статус и разобрать JSON.

    Функция вызывается методами клиентов, чтобы тесты могли подменять
    ``requests.get`` и не ходить в сеть.
    """
    try:
        response = requests.get(
            url, params=params, headers=headers, timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except ValueError as exc:
        # requests.JSONDecodeError является и ValueError, и RequestException.
        raise APIError("Сервис вернул ответ, который не является корректным JSON") from exc
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        detail = f"HTTP {status}" if status else str(exc)
        raise APIError(f"Ошибка запроса к {url}: {detail}") from exc


def _as_float(value: Any, default: float = 0.0) -> float:
    """Безопасно привести значение из ответа API к ``float``."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class NominatimAPI(GeoAPI):
    """Получение границ страны через Nominatim (OpenStreetMap)."""

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout
        self.headers = {"User-Agent": USER_AGENT}

    def _get_json(
        self, url: str, params: dict[str, Any] | None = None
    ) -> Any:
        return _fetch_json(
            url, params, headers=self.headers, timeout=self.timeout
        )

    def get_bounding_box(self, country: str) -> dict[str, float]:
        """Вернуть координаты ``south/north/west/east`` для страны.

        :raises ValueError: если страна не найдена или ответ некорректен.
        :raises APIError: если сервис недоступен или вернул ошибку.
        """
        if not isinstance(country, str) or not country.strip():
            raise ValueError("Название страны должно быть непустой строкой")

        data = self._get_json(
            NOMINATIM_URL,
            {"q": country.strip(), "format": "jsonv2", "limit": 1},
        )
        if not isinstance(data, list) or not data:
            raise ValueError(f"Страна '{country}' не найдена в Nominatim")

        box = data[0].get("boundingbox") if isinstance(data[0], dict) else None
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            raise ValueError("Nominatim вернул некорректный boundingbox")

        try:
            south, north, west, east = (float(value) for value in box)
        except (TypeError, ValueError) as exc:
            raise ValueError("Координаты boundingbox должны быть числами") from exc

        return {
            "south": south,
            "north": north,
            "west": west,
            "east": east,
        }


class OpenSkyAPI(FlightAPI):
    """Получение информации о самолётах через OpenSky Network."""

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout
        self.aeroplanes: list[dict[str, Any]] = []

    def _get_json(
        self, url: str, params: dict[str, Any] | None = None
    ) -> Any:
        return _fetch_json(url, params, timeout=self.timeout)

    @staticmethod
    def _validate_bounding_box(bounding_box: dict[str, float]) -> dict[str, float]:
        """Проверить границы прямоугольника и вернуть числа."""
        required = ("south", "north", "west", "east")
        if not isinstance(bounding_box, dict) or any(
            key not in bounding_box for key in required
        ):
            raise ValueError(
                "Ожидается dict с ключами south, north, west, east"
            )

        box = {
            key: _as_float(bounding_box[key], default=float("nan"))
            for key in required
        }
        if any(value != value for value in box.values()):  # проверка на NaN
            raise ValueError("Все координаты должны быть числами")
        if not -90 <= box["south"] <= box["north"] <= 90:
            raise ValueError("Некорректные значения широты (south/north)")
        if not -180 <= box["west"] <= 180 or not -180 <= box["east"] <= 180:
            raise ValueError("Некорректные значения долготы (west/east)")
        return box

    @staticmethod
    def _parse_state(state: Any) -> dict[str, Any] | None:
        """Преобразовать один элемент ответа OpenSky в словарь самолёта."""
        if not isinstance(state, (list, tuple)) or len(state) < 14:
            return None

        altitude = state[13] if state[13] is not None else state[7]
        return {
            "icao24": str(state[0] or ""),
            "callsign": str(state[1] or "").strip() or "UNKNOWN",
            "country": str(state[2] or "").strip() or "Unknown",
            "longitude": _as_float(state[5]),
            "latitude": _as_float(state[6]),
            "altitude": _as_float(altitude),
            "on_ground": bool(state[8]),
            "velocity": _as_float(state[9]),
        }

    def get_aeroplanes(
        self, bounding_box: dict[str, float]
    ) -> list[dict[str, Any]]:
        """Вернуть самолёты внутри прямоугольника координат.

        Если страна пересекает меридиан 180°, запрос делится на две части.
        """
        box = self._validate_bounding_box(bounding_box)
        areas = (
            [(box["west"], box["east"])]
            if box["west"] <= box["east"]
            else [(box["west"], 180.0), (-180.0, box["east"])]
        )

        states: list[dict[str, Any]] = []
        seen: set[str] = set()
        for west, east in areas:
            data = self._get_json(
                OPENSKY_URL,
                {
                    "lamin": box["south"],
                    "lomin": west,
                    "lamax": box["north"],
                    "lomax": east,
                },
            )
            raw_states = data.get("states") or [] if isinstance(data, dict) else []
            if not isinstance(raw_states, (list, tuple)):
                raise APIError("OpenSky вернул некорректный список самолётов")

            for raw_state in raw_states:
                plane = self._parse_state(raw_state)
                if plane is None:
                    continue
                key = plane["icao24"] or str(raw_state)
                if key not in seen:
                    seen.add(key)
                    states.append(plane)

        self.aeroplanes = states
        return states


class AeroplanesAPI:
    """Фасад: координаты страны -> самолёты в её воздушном пространстве."""

    def __init__(
        self, geocoder: GeoAPI | None = None, flights: FlightAPI | None = None
    ) -> None:
        self.geocoder: GeoAPI = geocoder or NominatimAPI()
        self.flights: FlightAPI = flights or OpenSkyAPI()

    def get_bounding_box(self, country: str) -> dict[str, float]:
        """Получить границы страны через геокодер."""
        return self.geocoder.get_bounding_box(country)

    def get_aeroplanes(self, country: str) -> list[dict[str, Any]]:
        """Получить самолёты в воздушном пространстве страны."""
        bounding_box = self.get_bounding_box(country)
        return self.flights.get_aeroplanes(bounding_box)
