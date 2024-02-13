from abc import ABC, abstractmethod
from datetime import UTC, date, datetime, tzinfo
from typing import Optional, Union

import pytz
from attrs import define
from dateutil.relativedelta import relativedelta

from octopus_stats.octo_api_reader import OctoAPIConfig

_dt_min_utc = datetime.min
_dt_min_utc = _dt_min_utc.replace(tzinfo=pytz.UTC)

class StorageManager(ABC):
    @abstractmethod
    def read_file_contents(self, filepath: str) -> str:
        raise NotImplementedError("Function read_file must be implemented")

    @abstractmethod
    def get_directory_listing(self, dirpath: str) -> list[str]:
        raise NotImplementedError("Function get_directory_listing must be implemented")


@define(kw_only=True, frozen=True)
class OctoExporterSettings:
    storage: StorageManager
    tz: tzinfo


class OctoExporter:
    def __init__(self, config: OctoAPIConfig, settings: OctoExporterSettings) -> None:
        self._config = config
        self._settings = settings
        self._storage = settings.storage

    def export(self, full: bool = False) -> None:
        if full:
            start_date = None
        else:
            start_date = self._get_next_start_date()

        self._read_consumption(start_date)

    def _read_consumption(self, start_date: Optional[datetime]):
        pass

    def _get_account_start_date(self):
        pass

    def _get_next_start_date(self) -> datetime | None:
        now = datetime.now(UTC)
        check = now.date()
        found_date: datetime | None = None

        # Dataframes are saved into partitioned directories named after the local time (HH-MM) of the latest consumption
        # record in the file. The file path will therefore be in the format YYYY/mm/dd/HH-MM e.g. 2023/12/01/22-30
        while not found_date and check > now.date() - relativedelta(years=1):
            latest_date = self._get_latest_processed_datetime(check)
            if latest_date:
                found_date = latest_date
                continue
            check = check - relativedelta(days=1)

        return found_date

    def _get_latest_processed_datetime(self, date: date) -> Union[datetime, None]:
        """
        Gets the latest-processed record datetime, based on the files present in the folder for a specified date. If no
        matching files are present, returns `None`.
        """
        date_dir = date.strftime("%Y/%m/%d")
        files = self._storage.get_directory_listing(date_dir)
        if not files:
            return None

        def date_from_filename(filename: str) -> datetime | None:
            try:
                return datetime.strptime(filename, "%Y/%m/%d/%H-%M").replace(tzinfo=self._settings.tz)
            except ValueError:
                return _dt_min_utc

        latest_date = max(
            [d for f in files if (d := date_from_filename(f)) is not None]
        )
        return latest_date if latest_date > _dt_min_utc else None
