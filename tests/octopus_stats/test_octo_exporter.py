from datetime import datetime
from pathlib import PurePosixPath

import pytest
import pytz
import time_machine
from octopus_stats.octo_exporter import (
    OctoAPIConfig,
    OctoExporter,
    OctoExporterSettings,
    StorageManager,
)


class FakeStorageManager(StorageManager):
    def __init__(self, files: dict[str, str]) -> None:
        super().__init__()
        self._files = files
        self._all_files = [PurePosixPath(f) for f in self._files]

    def read_file_contents(self, filepath: str) -> str:
        return self._files[filepath]

    def get_directory_listing(self, dirpath: str) -> list[str]:
        return [f.as_posix() for f in self._all_files if f.is_relative_to(dirpath)]


@time_machine.travel("2023-12-03 03:00 +0000")
def test_gets_correct_start_date_recent() -> None:
    # *** ARRANGE ***
    files = {
        "2023/11/29/23-30": "",
        "2023/11/30/23-30": "",
        "2023/12/01/20-00": "",
    }
    sm = FakeStorageManager(files)
    settings = OctoExporterSettings(storage=sm, tz=pytz.timezone("Europe/London"))
    config = OctoAPIConfig(api_key="1234", mpan="12345", serial_number="123456")
    sut = OctoExporter(config, settings)

    # *** ACT ***
    x = sut._get_next_start_date()

    # *** ASSERT ***
    expected = datetime(2023, 12, 1, 20, 0, tzinfo=pytz.timezone("Europe/London"))
    assert x == pytest.approx(expected, abs=10)

@time_machine.travel("2023-12-03 03:00 +0000")
def test_gets_correct_start_date_no_files() -> None:
    # *** ARRANGE ***
    files: dict[str, str] = {}
    sm = FakeStorageManager(files)
    settings = OctoExporterSettings(storage=sm, tz=pytz.timezone("Europe/London"))
    config = OctoAPIConfig(api_key="1234", mpan="12345", serial_number="123456")
    sut = OctoExporter(config, settings)

    # *** ACT ***
    x = sut._get_next_start_date()

    # *** ASSERT ***
    assert x is None
