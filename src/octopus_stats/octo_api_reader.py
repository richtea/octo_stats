import datetime
import os
from collections.abc import Generator
from typing import Any, Optional, Self, overload

import cattrs
import pendulum
import requests
from attrs import define, field, frozen, validators
from cattrs.gen import make_dict_structure_fn
from furl import furl  # type: ignore[reportMissingTypeStubs]
from requests.auth import HTTPBasicAuth

_BASE_URL = "https://api.octopus.energy/v1/"


@define(kw_only=True, frozen=True)
class OctoAPIConfig:
    api_key: str = field(validator=[validators.min_len(2)])
    mpan: Optional[str] = field(validator=[validators.min_len(2)])
    serial_number: Optional[str] = field(validator=[validators.min_len(2)])
    account_number: Optional[str] = field(validator=[validators.min_len(2)])

    @classmethod
    def from_env(cls, prefix: str = "OCTOPUS_") -> Self:
        """
        Instantiates a config instance from environment variables. Uses the following env vars (assuming the default
        prefix):
          - OCTOPUS_API_KEY
          - OCTOPUS_MPAN
          - OCTOPUS_SERIAL_NUMBER
          - OCTOPUS_ACCOUNT_NUMBER
        You must provide either the ACCOUNT_NUMBER or the MPAN + SERIAL_NUMBER.
        """
        api_key = os.environ.get(f"{prefix}API_KEY", None)
        mpan = os.environ.get(f"{prefix}MPAN", None)
        serial_number = os.environ.get(f"{prefix}SERIAL_NUMBER", None)
        account_number = os.environ.get(f"{prefix}ACCOUNT_NUMBER", None)
        if api_key is None:
            raise RuntimeError(
                "The API_KEY environment variable is missing"
            )
        if account_number is None and (mpan is None or serial_number is None):
            raise RuntimeError(
                "One of the configuration environment variables is missing"
            )
        return cls(api_key=api_key, mpan=mpan, serial_number=serial_number, account_number=account_number)


@frozen
class ConsumptionRecord:
    interval_start: datetime.datetime
    interval_end: datetime.datetime
    consumption: float


@frozen
class Agreement:
    tariff_code: str
    valid_from: datetime.datetime
    valid_to: Optional[datetime.datetime]


@frozen
class ElectricityMeterRegister:
    identifier: str
    rate: str
    is_settlement_register: bool


@frozen
class ElectricityMeter:
    serial_number: str
    registers: list[ElectricityMeterRegister] = field(factory=list)


@frozen
class ElectricityMeterPoint:
    mpan: str
    profile_class: int
    consumption_standard: int
    meters: list[ElectricityMeter] = field(factory=list)
    agreements: list[Agreement] = field(factory=list)


@frozen
class Property:
    id_: str = field(alias="id")
    moved_in_at: datetime.datetime
    moved_out_at: Optional[datetime.datetime]
    address_line_1: str
    address_line_2: str
    address_line_3: str
    town: str
    county: str
    postcode: str
    electricity_meter_points: list[ElectricityMeterPoint] = field(factory=list)


@frozen
class Account:
    number: str
    properties: list[Property] = field(factory=list)


class OctoAPIReader:
    def __init__(self, config: OctoAPIConfig) -> None:
        self._config = config
        self._converter = cattrs.Converter()
        self._converter.register_structure_hook(
            datetime.datetime, lambda ts, _: datetime.datetime.fromisoformat(ts)
        )
        hook = make_dict_structure_fn(Property, self._converter, _cattrs_use_alias=True)
        self._converter.register_structure_hook(Property, hook)

    @overload
    def get_consumption(
        self,
        *,
        mpan: str,
        serial_number: str,
        start: Optional[pendulum.DateTime] = None,
        end: Optional[pendulum.DateTime] = None,
    ) -> Generator[ConsumptionRecord, Any, None]:
        ...

    @overload
    def get_consumption(
        self,
        *,
        account_number: str,
        start: Optional[pendulum.DateTime] = None,
        end: Optional[pendulum.DateTime] = None,
    ) -> Generator[ConsumptionRecord, Any, None]:
        ...

    @overload
    def get_consumption(
        self,
        *,
        start: Optional[pendulum.DateTime] = None,
        end: Optional[pendulum.DateTime] = None,
        mpan: Optional[str] = None,
        serial_number: Optional[str] = None,
        account_number: Optional[str] = None,
    ) -> Generator[ConsumptionRecord, Any, None]:
        ...

    def get_consumption(  # noqa: PLR0913
        self,
        *,
        start: Optional[pendulum.DateTime] = None,
        end: Optional[pendulum.DateTime] = None,
        mpan: Optional[str] = None,
        serial_number: Optional[str] = None,
        account_number: Optional[str] = None,
    ) -> Generator[ConsumptionRecord, Any, None]:
        if account_number and not (mpan and serial_number):
            (mpan, serial_number) = self._get_default_meter(
                account_number=account_number
            )

        if not (mpan and serial_number):
            raise RuntimeError("mpan and serial_number are required")

        endpoint = (
            f"electricity-meter-points/{mpan}/meters/{serial_number}/consumption/"
        )
        if start is None:
            start = pendulum.DateTime.min
        if end is None:
            end = pendulum.DateTime.now()
        params = {
            "period_from": _to_octo8601(start),
            "period_to": _to_octo8601(end),
            "order_by": "period",
            "page_size": "200",
        }

        response = self._call_api(endpoint, params)

        for r in response["results"]:
            yield self._converter.structure(r, ConsumptionRecord)
        while response["next"]:
            response = self._call_api_raw(response["next"])
            for r in response["results"]:
                yield self._converter.structure(r, ConsumptionRecord)

    def get_account(self, account_number: str):
        endpoint = f"accounts/{account_number}"
        response = self._call_api(endpoint, {})
        return self._converter.structure(response, Account)

    def _get_default_meter(self, account_number: str) -> tuple[str, str]:
        account = self.get_account(account_number)
        meter_point = account.properties[-1].electricity_meter_points[-1]
        return (meter_point.mpan, meter_point.meters[-1].serial_number)

    def _call_api(self, endpoint: str, params: dict[str, str]) -> Any:
        f = furl(_BASE_URL)
        f /= endpoint
        f.add(args=params)
        return self._call_api_raw(f.url)

    def _call_api_raw(self, url: str):
        r = requests.get(url, auth=HTTPBasicAuth(self._config.api_key, ""), timeout=30)
        r.raise_for_status()
        return r.json()


def _to_octo8601(dt: pendulum.DateTime) -> str:
    """
    Return the ISO string representation of a datetime

    Seconds resolution only.

    Although the API doc says that the timezone should be included,
    it actually does not work.
    https://developer.octopus.energy/docs/api/#parameters

    Therefore the time is converted to UTC and
    returned as Z (zulu) time.

    :param dt: datetime object
    :return: date and time as string
    """
    return dt.in_timezone("UTC").replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
