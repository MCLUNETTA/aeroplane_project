"""Точка входа и взаимодействие с пользователем через консоль."""

from __future__ import annotations

from typing import Any

from src.aeroplane import Aeroplane
from src.api import AeroplanesAPI
from src.base_api import APIError
from src.base_storage import StorageError
from src.filters import (
    filter_aeroplanes,
    get_aeroplanes_by_altitude,
    get_top_aeroplanes,
    print_aeroplanes,
)
from src.json_saver import JSONSaver


def _read_top_n(raw: str) -> int:
    """Преобразовать ввод пользователя в положительное целое число."""
    try:
        top_n = int(raw.strip())
    except ValueError as exc:
        raise ValueError("Количество самолётов должно быть целым числом") from exc
    if top_n <= 0:
        raise ValueError("Количество самолётов должно быть больше нуля")
    return top_n


def user_interaction(
    api: AeroplanesAPI | Any = None, saver: JSONSaver | Any = None
) -> list[Aeroplane]:
    """Спросить параметры у пользователя и вывести результат.

    Запрос к API, фильтрация, сортировка и сохранение в JSON выполняются
    последовательно. Ошибки вводимых данных и внешних сервисов выводятся
    понятным сообщением, а не traceback.
    """
    api = api or AeroplanesAPI()
    saver = saver or JSONSaver()

    try:
        country = input("Введите название страны: ").strip()
        if not country:
            print("Название страны не может быть пустым.")
            return []

        top_n = _read_top_n(
            input("Введите количество самолётов для вывода в топ N: ")
        )
        filter_words = input(
            "Введите страны регистрации для фильтрации (через пробел): "
        ).split()
        altitude_range = input(
            "Введите диапазон высот (например, 100000 - 150000) "
            "или оставьте пустым: "
        )

        raw_aeroplanes = api.get_aeroplanes(country)
        aeroplanes = Aeroplane.cast_to_object_list(raw_aeroplanes)

        for aeroplane in aeroplanes:
            saver.add_aeroplane(aeroplane)

        filtered = filter_aeroplanes(aeroplanes, filter_words)
        ranged = get_aeroplanes_by_altitude(filtered, altitude_range)
        top_aeroplanes = get_top_aeroplanes(ranged, top_n)

        print(f"\nПолучено самолётов: {len(aeroplanes)}")
        destination = getattr(saver, "file_path", "хранилище")
        print(f"Данные сохранены в {destination}")
        print(f"Топ-{top_n} по высоте полёта:")
        print_aeroplanes(top_aeroplanes)
        return top_aeroplanes

    except (EOFError, KeyboardInterrupt):
        print("\nВвод прерван.")
        return []
    except (APIError, StorageError, TypeError, ValueError) as exc:
        print(f"Ошибка: {exc}")
        return []
    except Exception as exc:  # пользователь не должен видеть traceback
        print(f"Непредвиденная ошибка: {exc}")
        return []


def main() -> None:
    """Запустить консольное приложение."""
    user_interaction()


if __name__ == "__main__":
    main()
