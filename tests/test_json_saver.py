import json

import pytest

from src.aeroplane import Aeroplane
from src.base_storage import BaseStorage, StorageError
from src.json_saver import JSONSaver


@pytest.fixture
def plane() -> Aeroplane:
    return Aeroplane("UAL1621", "United States", 268.79, 10203.18, "abc123")


@pytest.fixture
def saver(tmp_path) -> JSONSaver:
    return JSONSaver(tmp_path / "data" / "planes.json")


def test_saver_implements_abc(saver):
    assert isinstance(saver, BaseStorage)
    assert json.loads(saver.file_path.read_text(encoding="utf-8")) == []


def test_add_get_and_delete(saver, plane):
    other = Aeroplane("AFR123", "France", 200.0, 8000.0, "ff0001")

    saver.add_aeroplane(plane)
    saver.add_aeroplane(other)

    assert len(saver.get_aeroplanes()) == 2
    assert [p.callsign for p in saver.get_aeroplanes(country="united states")] == [
        "UAL1621"
    ]
    assert saver.get_aeroplanes(velocity=200.0)[0].country == "France"
    assert len(saver.get_aeroplanes(icao24="abc123")) == 1

    saved = json.loads(saver.file_path.read_text(encoding="utf-8"))
    assert saved[0]["callsign"] == "UAL1621"

    assert saver.delete_aeroplane(plane) is True
    assert saver.delete_aeroplane(plane) is False
    assert [p.callsign for p in saver.get_aeroplanes()] == ["AFR123"]


def test_delete_without_icao_uses_all_fields(saver, plane):
    saver.add_aeroplane(plane)
    twin_without_id = Aeroplane("UAL1621", "United States", 268.79, 10203.18)

    assert saver.delete_aeroplane(twin_without_id) is True
    assert saver.get_aeroplanes() == []


def test_saver_rejects_invalid_arguments(saver):
    with pytest.raises(TypeError):
        saver.add_aeroplane({"callsign": "X"})
    with pytest.raises(TypeError):
        saver.delete_aeroplane("UAL1621")
    with pytest.raises(ValueError, match="Неизвестные критерии"):
        saver.get_aeroplanes(unknown_field=1)


def test_saver_reports_corrupted_file(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json}", encoding="utf-8")
    saver = JSONSaver(broken)

    with pytest.raises(StorageError):
        saver.get_aeroplanes()

    broken.write_text('{"callsign": "X"}', encoding="utf-8")
    with pytest.raises(StorageError):
        saver.get_aeroplanes()

    broken.write_text('[{"callsign": "X"}]', encoding="utf-8")
    with pytest.raises(StorageError):
        saver.get_aeroplanes()


def test_saver_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "deep" / "planes.json"
    saver = JSONSaver(path)
    assert path.exists()
    assert saver.get_aeroplanes() == []
