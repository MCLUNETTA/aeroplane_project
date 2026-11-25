"""Абстрактный класс хранилища самолётов."""

from abc import ABC, abstractmethod
from typing import Any

from src.aeroplane import Aeroplane


class StorageError(Exception):
    """Ошибка чтения или записи хранилища."""


class BaseStorage(ABC):
    """Контракт хранилища: добавить, получить по критериям, удалить.

    Реализация может быть JSON-файлом, БД или удалённым хранилищем —
    остальная программа зависит только от этого интерфейса.
    """

    @abstractmethod
    def add_aeroplane(self, aeroplane: Aeroplane) -> None:
        """Добавить один самолёт в хранилище."""

    @abstractmethod
    def get_aeroplanes(self, **criteria: Any) -> list[Aeroplane]:
        """Вернуть самолёты, подходящие под критерии (все, если пусто)."""

    @abstractmethod
    def delete_aeroplane(self, aeroplane: Aeroplane) -> bool:
        """Удалить самолёт. Вернуть True, если что-то было удалено."""
