"""Класс, описывающий один самолёт."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Iterable


@dataclass
class Aeroplane:
    """Информация о самолёте.

    Атрибуты:
        callsign: позывной (например, ``UAL1621``).
        country: страна регистрации ( ``origin_country`` из ответа OpenSky).
        velocity: скорость полёта в м/с.
        altitude: высота полёта в метрах.
        icao24: уникальный идентификатор самолёта.
        on_ground: находится ли самолёт на земле.
    """

    callsign: str
    country: str
    velocity: float
    altitude: float
    icao24: str = ""
    on_ground: bool = False

    _ALIASES = {
        "origin_country": "country",
        "speed": "velocity",
        "geo_altitude": "altitude",
        "baro_altitude": "altitude",
    }

    def __post_init__(self) -> None:
        self.callsign = self._validate_text(self.callsign, "callsign")
        self.country = self._validate_text(self.country, "country")
        self.velocity = self._validate_number(self.velocity, "velocity")
        self.altitude = self._validate_number(self.altitude, "altitude")
        self.icao24 = self._validate_optional_text(self.icao24, "icao24")
        self.on_ground = self._validate_bool(self.on_ground, "on_ground")

    @staticmethod
    def _validate_text(value: Any, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} должно быть непустой строкой")
        return value.strip()

    @staticmethod
    def _validate_optional_text(value: Any, name: str) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError(f"{name} должно быть строкой")
        return value.strip()

    @staticmethod
    def _validate_number(value: Any, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} должно быть числом")
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            raise ValueError(f"{name} должно быть конечным числом")
        if number < 0:
            raise ValueError(f"{name} не может быть отрицательным")
        return number

    @staticmethod
    def _validate_bool(value: Any, name: str) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"{name} должно быть bool")
        return value

    @staticmethod
    def _ensure_aeroplane(other: Any) -> Aeroplane:
        if not isinstance(other, Aeroplane):
            raise TypeError("Сравнение возможно только с объектом Aeroplane")
        return other

    def compare_by_velocity(self, other: Aeroplane) -> int:
        """Сравнить скорость: -1 меньше, 0 равно, 1 больше."""
        other = self._ensure_aeroplane(other)
        return (self.velocity > other.velocity) - (self.velocity < other.velocity)

    def compare_by_altitude(self, other: Aeroplane) -> int:
        """Сравнить высоту: -1 меньше, 0 равно, 1 больше."""
        other = self._ensure_aeroplane(other)
        return (self.altitude > other.altitude) - (self.altitude < other.altitude)

    def is_faster_than(self, other: Aeroplane) -> bool:
        """Вернуть True, если этот самолёт быстрее."""
        return self.compare_by_velocity(other) > 0

    def is_higher_than(self, other: Aeroplane) -> bool:
        """Вернуть True, если этот самолёт выше."""
        return self.compare_by_altitude(other) > 0

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Aeroplane):
            return NotImplemented
        return self.compare_by_altitude(other) < 0

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, Aeroplane):
            return NotImplemented
        return self.compare_by_altitude(other) > 0

    def to_dict(self) -> dict[str, Any]:
        """Представить самолёт в виде словаря для JSON."""
        return asdict(self)

    @classmethod
    def cast_to_object_list(cls, items: Iterable[Any]) -> list[Aeroplane]:
        """Преобразовать набор словарей (или самолётов) в список объектов."""
        if items is None or isinstance(items, (str, bytes, dict)):
            raise TypeError("Ожидается итерируемый набор словарей с самолётами")

        result: list[Aeroplane] = []
        allowed = {field.name for field in fields(cls)}
        for index, item in enumerate(items):
            if isinstance(item, cls):
                result.append(item)
                continue
            if not isinstance(item, dict):
                raise TypeError(f"Элемент #{index} не является словарём")

            payload = dict(item)
            for alias, field_name in cls._ALIASES.items():
                if alias in payload and field_name not in payload:
                    payload[field_name] = payload[alias]
            payload = {
                key: value for key, value in payload.items() if key in allowed
            }
            try:
                result.append(cls(**payload))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Неверные данные самолёта #{index}: {exc}"
                ) from exc
        return result

    def __str__(self) -> str:
        return (
            f"{self.callsign} | {self.country} | "
            f"{self.velocity:.1f} м/с | {self.altitude:.0f} м"
        )
