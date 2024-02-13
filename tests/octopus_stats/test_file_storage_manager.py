from pathlib import Path

import pytest
from octopus_stats.file_storage_manager import FileStorageManager, FileStorageSettings


@pytest.fixture(autouse=True)
def change_test_dir( # noqa: PT004
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Ensures that we chdir into the parent folder of the test script module before each test, and back again afterwards.
    """
    monkeypatch.chdir(request.path.parent)


def test_relative_basepath() -> None:
    # *** ARRANGE ***

    settings = FileStorageSettings(base_dir="./test_file_storage_manager/root")
    sut = FileStorageManager(settings)

    # *** ACT ***
    basepath = sut.basepath

    # *** ASSERT ***
    assert basepath == Path(__file__).parent.joinpath("test_file_storage_manager/root")


def test_get_directory_listing_root() -> None:
    # *** ARRANGE ***

    settings = FileStorageSettings(base_dir="./test_file_storage_manager/root")
    sut = FileStorageManager(settings)

    # *** ACT ***
    files = sut.get_directory_listing("")

    # *** ASSERT ***
    assert files == ["rootfile01.txt"]


def test_get_directory_listing_subdir() -> None:
    # *** ARRANGE ***

    settings = FileStorageSettings(base_dir="./test_file_storage_manager/root")
    sut = FileStorageManager(settings)

    # *** ACT ***
    files = sut.get_directory_listing("2023/12/21")

    # *** ASSERT ***
    assert files == ["2023/12/21/21-00", "2023/12/21/23-30"]
