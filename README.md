# Трекер самолётов

Курсовая работа: приложение получает границы выбранной страны через
[Nominatim](https://nominatim.org/release-docs/develop/api/Search/), запрашивает
самолёты в этом прямоугольнике через
[OpenSky Network](https://openskynetwork.github.io/opensky-api/rest.html),
сохраняет результат в JSON и показывает пользователю топ по высоте полёта.

## Структура

```text
.
├── data/
│   └── aeroplanes.json      # результат работы программы
├── logs/
├── reports/
├── scripts/
├── src/
│   ├── __init__.py
│   ├── aeroplane.py         # класс Aeroplane, валидация и сравнение
│   ├── api.py               # NominatimAPI, OpenSkyAPI, AeroplanesAPI
│   ├── base_api.py          # ABC для API-клиентов
│   ├── base_storage.py      # ABC хранилища
│   ├── filters.py           # фильтрация, сортировка, топ-N, вывод
│   ├── json_saver.py        # JSONSaver
│   └── main.py              # консольное взаимодействие
├── tests/
│   ├── test_aeroplane.py
│   ├── test_api.py
│   ├── test_filters.py
│   ├── test_json_saver.py
│   └── test_main.py
├── main.py                  # алиас для `python main.py`
├── pyproject.toml
├── poetry.lock
└── requirements.txt
```

## Установка

Рекомендуемый способ — Poetry:

```bash
poetry install
poetry run pytest --cov=src --cov-report=term-missing
poetry run python -m src.main
# или: poetry run python main.py
```

Без Poetry:

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
pytest --cov=src --cov-report=term-missing
python -m src.main
# или: python main.py
```

## Использование

Программа задаёт четыре вопроса:

1. название страны для поиска (например, `Spain`);
2. `N` — сколько самолётов показать в топе;
3. страны регистрации для фильтрации через пробел (можно оставить пустым);
4. диапазон высот вида `100000 - 150000` (можно оставить пустым).

Пример:

```text
Введите название страны: Spain
Введите количество самолётов для вывода в топ N: 3
Введите страны регистрации для фильтрации (через пробел): Spain France
Введите диапазон высот (например, 100000 - 150000) или оставьте пустым: 9000 - 13000
```

Все найденные самолёты добавляются в `data/aeroplanes.json`, а на экран
выводится отфильтрованная и отсортированная по высоте (DESC) выборка.

> OpenSky отдаёт анонимные запросы с ограничением по частоте. Если сервис
> вернёт `429 Too Many Requests`, программа напечатает понятную ошибку и не
> упадёт. Повторите запрос позже или используйте свои учётные данные.

## Архитектура (SOLID)

- `BaseAPI`, `GeoAPI`, `FlightAPI` и `BaseStorage` — абстрактные классы;
  конкретные клиенты и хранилища реализуют только свои обязанности (ISP, DIP).
- `AeroplanesAPI` — фасад, который собирает данные двух сервисов; зависимости
  передаются в конструктор, что упрощает тестирование.
- `Aeroplane` инкапсулирует данные и проверяет их при создании; сравнение по
  скорости и высоте доступно через `compare_by_velocity`,
  `compare_by_altitude`, `is_faster_than`, `is_higher_than` и операторы `>`, `<`.
- `JSONSaver` можно заменить другой реализацией `BaseStorage` (БД, API) без
  изменений в остальном коде.

## Тесты

```bash
pytest --cov=src --cov-report=term-missing
```
