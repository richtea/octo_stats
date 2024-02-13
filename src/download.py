#! /usr/bin/env python

# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false

import datetime
from pathlib import Path
from typing import Any

import dotenv
import fastparquet
import pandas as pd
import pendulum
from octopus_stats import (
    ConsumptionRecord,
    OctoAPIConfig,
    OctoAPIReader,
)
from zappi_stats.zappi_api_reader import MyenergiApiConfig, ZappiApiReader


def get_consumption_data(cr: ConsumptionRecord) -> dict[str, Any]:
    cd: dict[str, Any] = {}
    cd["start_utc"] = cr.interval_start.astimezone(datetime.UTC)
    cd["end_utc"] = cr.interval_end.astimezone(datetime.UTC)
    cd["total_consumed_kwh"] = cr.consumption
    cd["start_local"] = cr.interval_start.replace(tzinfo=None)
    cd["end_local"] = cr.interval_end.replace(tzinfo=None)
    cd["start_utc_offset"] = cr.interval_start.utcoffset()
    cd["end_utc_offset"] = cr.interval_end.utcoffset()
    return cd


def write_batch(batch: list[ConsumptionRecord]) -> None:
    if not batch:
        return
    df_consumption = pd.DataFrame([get_consumption_data(cr) for cr in batch])
    df_consumption["duration"] = df_consumption["end_utc"] - df_consumption["start_utc"]
    df_consumption["date_local"] = df_consumption["start_local"].dt.normalize()
    df_consumption["dayofyear_local"] = df_consumption["start_local"].dt.dayofyear
    df_consumption["dayofweek_local"] = df_consumption["start_local"].dt.dayofweek
    df_consumption["hourofday_local"] = [r.hour for r in df_consumption["start_local"]]

    opts: dict[str, Any] = {
        "partition_on": "date_local",
        "compression": "GZIP",
        "file_scheme": "hive",
    }
    parquet_file = Path("test.parquet").resolve()
    if parquet_file.exists():
        opts["append"] = True
    fastparquet.write("test.parquet", df_consumption, **opts)


def octo():
    dotenv.load_dotenv()
    config = OctoAPIConfig.from_env()
    api_reader = OctoAPIReader(config)
    my_tz = "Europe/London"
    params: dict[str, Any] = {
        "start": pendulum.datetime(2024, 1, 2, 0, 0, tz=my_tz),
        "end": pendulum.datetime(2024, 1, 3, 0, 0, tz=my_tz),
    }
    if config.mpan is None or config.serial_number is None:
        params["account_number"] = config.account_number
    else:
        params["mpan"] = config.mpan
        params["serial_number"] = config.serial_number
    consumption = api_reader.get_consumption(**params)
    current_date = pendulum.Date.min
    current_batch: list[ConsumptionRecord] = []
    for r in consumption:
        local_start_date = r.interval_start.date()
        if local_start_date != current_date:
            write_batch(current_batch)
            current_date = local_start_date
        current_batch.append(r)
    write_batch(current_batch)


def zappi() -> None:
    dotenv.load_dotenv()
    config = MyenergiApiConfig.from_env()
    my_tz = "Europe/London"
    api = ZappiApiReader(config)
    api.connect()
    print(api.connected_host)
    for x in api.get_data(
        pendulum.datetime(2024, 1, 2, 0, 0, tz=my_tz),
        pendulum.datetime(2024, 1, 28, 0, 0, tz=my_tz),
    ):
        print(x)


def main() -> None:
    zappi()


if __name__ == "__main__":
    main()
