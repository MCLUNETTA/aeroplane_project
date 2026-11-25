"""Функции фильтрации, сортировки и вывода самолётов."""

from __future__ import annotations

import re
from dataclasses import fields
from typing import Any, Iterable

from src.aeroplane import Aeroplane

_RANGE_PATTERN = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*"
    r"(?:[-–—]|до|to)\s*"
    r"(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*$",
    re.IGNORECASE,
)

_COUNTRY_ALIASES = {
    "сша": "united states",
    "usa": "united states",
    "рф": "russia",
}


def _to_aeroplanes(aeroplanes: Iterable[Any]) -> list[Aeroplane]:
    """Привести набор словарей или объектов к списку ``Aeroplane``."""
    items = list(aeroplanes)
    if items and all(isinstance(item, dict) for item in items):
        return Aeroplane.cast_to_object_list(items)
    if not all(isinstance(item, Aeroplane) for item in items):
        raise TypeError("Ожидаются объекты Aeroplane или словари с их данными")
    return items


def filter_aeroplanes(
    aeroplanes: Iterable[Any], countries: Iterable[str] | str | None
) -> list[Aeroplane]:
    """Отфильтровать самолёты по стране регистрации.

    Поиск регистронезависимый и по подстроке, поэтому ``"united"`` найдёт
    ``"United States"``. Пустой список стран означает «без фильтра».
    """
    planes = _to_aeroplanes(aeroplanes)
    if countries is None:
        return planes
    if isinstance(countries, str):
        countries = [countries]

    try:
        words = [
            str(country).strip().casefold()
            for country in countries
            if str(country).strip()
        ]
    except TypeError as exc:
        raise TypeError("Не удалось разобрать список стран") from exc

    if not words:
        return planes

    normalized: list[str] = []
    for word in words:
        normalized.append(word)
        if word in _COUNTRY_ALIASES:
            normalized.append(_COUNTRY_ALIASES[word])

    return [
        plane
        for plane in planes
        if any(word in plane.country.casefold() for word in normalized)
    ]


def parse_altitude_range(
    altitude_range: str | tuple[Any, Any] | list[Any] | None,
) -> tuple[float, float]:
    """Разобрать диапазон высот вида ``"100000 - 150000"``.

    Пустая строка или ``None`` означают отсутствие ограничений.
    """
    if altitude_range is None:
        return float("-inf"), float("inf")
    if isinstance(altitude_range, str):
        if not altitude_range.strip():
            return float("-inf"), float("inf")
        match = _RANGE_PATTERN.match(altitude_range)
        if not match:
            raise ValueError(
                "Некорректный диапазон высот. Пример: 100000 - 150000"
            )
        low, high = float(match.group(1)), float(match.group(2))
    elif isinstance(altitude_range, (tuple, list)) and len(altitude_range) == 2:
        try:
            low, high = float(altitude_range[0]), float(altitude_range[1])
        except (TypeError, ValueError) as exc:
            raise ValueError("Границы диапазона должны быть числами") from exc
    else:
        raise ValueError("Ожидается строка вида '100000 - 150000'")

    if low > high:
        raise ValueError("Первая граница диапазона должна быть меньше второй")
    return low, high


def get_aeroplanes_by_altitude(
    aeroplanes: Iterable[Any],
    altitude_range: str | tuple[Any, Any] | list[Any] | None,
) -> list[Aeroplane]:
    """Отобрать самолёты с высотой внутри заданного диапазона."""
    low, high = parse_altitude_range(altitude_range)
    return [
        plane
        for plane in _to_aeroplanes(aeroplanes)
        if low <= plane.altitude <= high
    ]


def sort_aeroplanes(
    aeroplanes: Iterable[Any], by: str = "altitude", reverse: bool = True
) -> list[Aeroplane]:
    """Отсортировать самолёты по атрибуту (по умолчанию — высота, DESC)."""
    valid_fields = {field.name for field in fields(Aeroplane)}
    if by not in valid_fields:
        raise ValueError(f"Неизвестный атрибут для сортировки: {by}")
    if not isinstance(reverse, bool):
        raise TypeError("reverse должен быть bool")
    return sorted(
        _to_aeroplanes(aeroplanes), key=lambda plane: getattr(plane, by), reverse=reverse
    )


def get_top_aeroplanes(
    aeroplanes: Iterable[Any], top_n: int
) -> list[Aeroplane]:
    """Вернуть топ-N самолётов по высоте полёта (DESC)."""
    if isinstance(top_n, bool) or not isinstance(top_n, int):
        raise ValueError("Количество самолётов должно быть целым числом")
    if top_n <= 0:
        raise ValueError("Количество самолётов должно быть больше нуля")
    return sort_aeroplanes(aeroplanes)[:top_n]


def print_aeroplanes(aeroplanes: Iterable[Any]) -> None:
    """Вывести самолёты в читаемой таблице."""
    planes = list(aeroplanes)
    if not planes:
        print("Самолёты не найдены.")
        return

    print(f"{'№':>3}  {'Позывной':<12} {'Страна':<20} {'Скорость, м/с':>13} {'Высота, м':>10}")
    print("-" * 64)
    for index, plane in enumerate(planes, start=1):
        print(
            f"{index:>3}  {plane.callsign:<12} {plane.country:<20} "
            f"{plane.velocity:>13.1f} {plane.altitude:>10.0f}"
        )
