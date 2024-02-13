import os

import pendulum
from octopus_stats.octo_api_reader import OctoAPIConfig, OctoAPIReader

account_number = os.environ.get("OCTOPUS_ACCOUNT_NUMBER", None)


def test_read_consumption() -> None:
    config = OctoAPIConfig.from_env()
    reader = OctoAPIReader(config)
    tz_london = "Europe/London"
    for r in reader.get_consumption(
        start=pendulum.datetime(2023, 12, 29, 0, 0, tz=tz_london),
        end=pendulum.datetime(2023, 12, 30, 0, 0, tz=tz_london),
        account_number=account_number,
    ):
        print(r)


def test_read_accounts() -> None:
    config = OctoAPIConfig.from_env()
    reader = OctoAPIReader(config)
    x = reader.get_account(account_number) # type: ignore
    print(x)
