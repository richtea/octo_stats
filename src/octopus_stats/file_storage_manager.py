from pathlib import Path

from attrs import define

from octopus_stats.octo_exporter import StorageManager


@define(kw_only=True, frozen=True)
class FileStorageSettings:
    base_dir: str

class FileStorageManager(StorageManager):
    def __init__(self, settings: FileStorageSettings) -> None:
        super().__init__()
        self._basepath = Path(settings.base_dir).resolve(strict=True)
        self._settings = settings

    @property
    def basepath(self) -> Path:
        return self._basepath

    def read_file_contents(self, filepath: str) -> str:
        if Path(filepath).is_absolute():
            raise ValueError("filepath must be a relative path")
        filename = self._basepath.joinpath(filepath)
        with filename.open() as f:
            content = f.read()
            return content


    def get_directory_listing(self, dirpath: str) -> list[str]:
        if Path(dirpath).is_absolute():
            raise ValueError("dirpath must be a relative path")
        target_dir = self._basepath.joinpath(dirpath)
        paths = target_dir.glob("*")
        files = [p.relative_to(self._basepath).as_posix() for p in paths if p.is_file()]
        files.sort()
        return files
