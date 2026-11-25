"""Абстрактные классы для работы с внешними API.

Здесь описаны только «контракты» клиентов: какой метод должен быть у каждого
сервиса. Конкретная реализация запросов находится в модуле :mod:`src.api`.
"""

from abc import ABC, abstractmethod
from typing import Any


class APIError(Exception):
    """Ошибка взаимодействия с внешним сервисом."""


class BaseAPI(ABC):
    """Базовый абстрактный класс для любого HTTP-клиента."""

    @abstractmethod
    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """Выполнить GET-запрос и вернуть разобранный JSON-ответ."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


class GeoAPI(BaseAPI, ABC):
    """Контракт сервиса, который умеет находить координаты страны."""

    @abstractmethod
    def get_bounding_box(self, country: str) -> dict[str, float]:
        """Вернуть границы страны в формате south/north/west/east."""


class FlightAPI(BaseAPI, ABC):
    """Контракт сервиса, который умеет находить самолёты в регионе."""

    @abstractmethod
    def get_aeroplanes(
        self, bounding_box: dict[str, float]
    ) -> list[dict[str, Any]]:
        """Вернуть список самолётов внутри прямоугольника координат."""
