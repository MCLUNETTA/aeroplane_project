"""Хранилище самолётов в JSON-файле."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Any

from src.aeroplane import Aeroplane
from src.base_storage import BaseStorage, StorageError

DEFAULT_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "aeroplanes.json"


class JSONSaver(BaseStorage):
    """Сохраняет список самолётов в JSON-файл.

    Файл представляет собой корректный JSON-массив объектов, например:

    ``[{"callsign": "UAL1621", "country": "United States", ...}]``
    """

    def __init__(self, file_path: str | Path = DEFAULT_DATA_FILE) -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists() or not self.file_path.read_text(
            encoding="utf-8"
        ).strip():
            self._write([])

    def _read(self) -> list[dict[str, Any]]:
        """Прочитать JSON-файл и вернуть список словарей."""
        try:
            content = self.file_path.read_text(encoding="utf-8")
            if not content.strip():
                return []
            data = json.loads(content)
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Не удалось прочитать {self.file_path}: {exc}") from exc

        if not isinstance(data, list):
            raise StorageError("JSON-файл должен содержать список самолётов")
        if not all(isinstance(item, dict) for item in data):
            raise StorageError("Каждая запись в JSON-файле должна быть объектом")
        return data

    def _write(self, data: list[dict[str, Any]]) -> None:
        """Записать список словарей в JSON-файл."""
        try:
            self.file_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise StorageError(f"Не удалось записать {self.file_path}: {exc}") from exc

    @staticmethod
    def _check_aeroplane(aeroplane: Any) -> Aeroplane:
        if not isinstance(aeroplane, Aeroplane):
            raise TypeError("Ожидается объект класса Aeroplane")
        return aeroplane

    def add_aeroplane(self, aeroplane: Aeroplane) -> None:
        """Добавить самолёт в конец файла."""
        aeroplane = self._check_aeroplane(aeroplane)
        data = self._read()
        data.append(aeroplane.to_dict())
        self._write(data)

    def get_aeroplanes(self, **criteria: Any) -> list[Aeroplane]:
        """Вернуть самолёты из файла, отфильтрованные по атрибутам.

        Строки сравниваются без учёта регистра, остальные значения —
        по точному совпадению.
        """
        valid_fields = {field.name for field in fields(Aeroplane)}
        unknown = set(criteria) - valid_fields
        if unknown:
            raise ValueError(f"Неизвестные критерии: {', '.join(sorted(unknown))}")

        data = self._read()
        try:
            aeroplanes = Aeroplane.cast_to_object_list(data)
        except (TypeError, ValueError) as exc:
            raise StorageError(f"Некорректные данные в файле: {exc}") from exc

        result = aeroplanes
        for key, value in criteria.items():
            if isinstance(value, str):
                result = [
                    plane
                    for plane in result
                    if getattr(plane, key).casefold() == value.casefold()
                ]
            else:
                result = [plane for plane in result if getattr(plane, key) == value]
        return result

    def delete_aeroplane(self, aeroplane: Aeroplane) -> bool:
        """Удалить самолёт из файла.

        Если известен ``icao24``, удаляется запись с этим идентификатором,
        иначе — запись со всеми совпадающими атрибутами.
        """
        aeroplane = self._check_aeroplane(aeroplane)
        data = self._read()

        def matches(item: dict[str, Any]) -> bool:
            if aeroplane.icao24 and item.get("icao24"):
                return str(item["icao24"]) == aeroplane.icao24
            try:
                candidate = Aeroplane.cast_to_object_list([item])[0]
            except (TypeError, ValueError):
                return False
            expected = aeroplane.to_dict()
            actual = candidate.to_dict()
            if not aeroplane.icao24:
                expected.pop("icao24")
                actual.pop("icao24")
            return actual == expected

        remaining = [item for item in data if not matches(item)]
        removed = len(remaining) != len(data)
        if removed:
            self._write(remaining)
        return removed
