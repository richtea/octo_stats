import datetime
import os
from collections.abc import Generator
from typing import Optional, Self
from urllib.parse import urlparse, urlunsplit

import pendulum
import requests
from attrs import define, frozen
from requests.auth import HTTPDigestAuth


@frozen(kw_only=True)
class ZappiUsageByMinuteRecordRaw:
    """1-minute Zappi usage record, raw format"""

    interval_start: datetime.datetime
    """Start of 1-minute interval (UTC)"""
    imp: int
    """Imported (joules)"""
    gep: int
    """Generated (joules)"""
    exp: int
    """Exported (joules)"""
    h1b: int
    """Zappi imported phase 1 (joules)"""
    h2b: int
    """Zappi imported phase 2 (joules)"""
    h3b: int
    """Zappi imported phase 3 (joules)"""
    h1d: int
    """Zappi diverted phase 1 (joules)"""
    h2d: int
    """Zappi diverted phase 2 (joules)"""
    h3d: int
    """Zappi diverted phase 3 (joules)"""
    v1: int
    """Voltage phase 1 (decivolts)"""
    v2: int
    """Voltage phase 2 (decivolts)"""
    v3: int
    """Voltage phase 3 (decivolts)"""
    frq: int
    """Frequency (centihertz)"""


def _create_usage_record(rec: dict[str, int]) -> ZappiUsageByMinuteRecordRaw:
    year = rec.get("yr", 0)
    month = rec.get("mon", 0)
    day = rec.get("dom", 0)
    hour = rec.get("hr", 0)
    minute = rec.get("min", 0)
    return ZappiUsageByMinuteRecordRaw(
        interval_start=datetime.datetime(
            year, month, day, hour, minute, tzinfo=datetime.UTC
        ),
        imp=rec.get("imp", 0),
        gep=rec.get("gep", 0),
        exp=rec.get("exp", 0),
        h1b=rec.get("h1b", 0),
        h2b=rec.get("h2b", 0),
        h3b=rec.get("h3b", 0),
        h1d=rec.get("h1d", 0),
        h2d=rec.get("h2d", 0),
        h3d=rec.get("h3d", 0),
        v1=rec.get("v1", 0),
        v2=rec.get("v2", 0),
        v3=rec.get("v3", 0),
        frq=rec.get("frq", 0),
    )


@define(kw_only=True, frozen=True)
class MyenergiApiConfig:
    hub_serial_number: str
    api_key: str

    @classmethod
    def from_env(cls, prefix: str = "MYENERGI_") -> Self:
        """
        Instantiates a config instance from environment variables. Uses the following env vars (assuming the default
        prefix):
          - MYENERGI_HUB_SERIAL_NUMBER
          - MYENERGI_API_KEY
        """
        api_key = os.environ.get(f"{prefix}API_KEY", None)
        hub_serial_number = os.environ.get(f"{prefix}HUB_SERIAL_NUMBER", None)
        if api_key is None:
            raise RuntimeError(f"The {prefix}API_KEY environment variable is missing")
        if hub_serial_number is None:
            raise RuntimeError(
                f"The {prefix}HUB_SERIAL_NUMBER environment variable is missing"
            )
        return cls(api_key=api_key, hub_serial_number=hub_serial_number)


DIRECTOR_URL = "https://director.myenergi.net/"
ASN_HEADER = "x_myenergi-asn"
MAX_ASN_REDIRECTS = 3


class ZappiApiReader:
    def __init__(self, config: MyenergiApiConfig) -> None:
        self._config = config
        self._host: Optional[str] = None

    def connect(self) -> None:
        # We need to determine the hostname to connect to - for a description of the protocol, see
        # https://myenergi.info/update-to-active-server-redirects-t2980.html
        url = DIRECTOR_URL
        attempt = 0
        while attempt < MAX_ASN_REDIRECTS:
            r = requests.get(
                url,
                auth=HTTPDigestAuth(
                    self._config.hub_serial_number, self._config.api_key
                ),
                timeout=30,
            )
            asn = r.headers.get(ASN_HEADER, None)
            if asn is None:
                raise RuntimeError(f"Header {ASN_HEADER} not present")
            parsed_url = urlparse(url)
            current_host = parsed_url.hostname
            if not current_host:
                raise RuntimeError("Unable to parse host")
            if current_host == asn:
                self._host = current_host
                break
            # Replace the hostname with ASN and try again
            url = parsed_url._replace(
                netloc=parsed_url.netloc.replace(current_host, asn)
            ).geturl()

        if self._host is None:
            raise RuntimeError("Unable to determine API host")

    def get_data(
        self,
        start: pendulum.DateTime,
        end: pendulum.DateTime,
    ) -> Generator[ZappiUsageByMinuteRecordRaw, None, None]:
        assert self.is_connected

        zappi_id = self._config.hub_serial_number
        sh = 0
        sm = 0
        mc = 1440

        start_utc = start.set(tz="UTC")
        end_utc = end.set(tz="UTC")
        period = pendulum.interval(start_utc, end_utc)
        for dt in period.range("days"):
            path = f"cgi-jday-Z{zappi_id}-{dt.year}-{dt.month}-{dt.day}-{sh}-{sm}-{mc}"
            url = urlunsplit(("https", self._host, path, "", ""))
            r = requests.get(
                url,
                auth=HTTPDigestAuth(
                    self._config.hub_serial_number, self._config.api_key
                ),
                timeout=30,
            )
            results = r.json()
            for x in results[f"U{zappi_id}"]:
                rec = _create_usage_record(x)
                if rec.interval_start >= start_utc and rec.interval_start < end_utc:
                    yield rec

    @property
    def is_connected(self) -> bool:
        return self._host is not None

    @property
    def connected_host(self) -> str:
        if self._host is None:
            raise RuntimeError("Not connected")
        return self._host
