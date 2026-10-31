"""ENSO data from the Oceanic Niño Index (ONI) of NOAA CPC."""

from __future__ import annotations

import math
import time

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
CACHE_SECONDS = 24 * 3600
RETRY_SECONDS = 3600  # The wait after a failed or stopped request.
# The lower limit of each strength class, in degrees Celsius of ONI anomaly.
STRENGTH_FLOORS = (
    (2.0, "very_strong"),
    (1.5, "strong"),
    (1.0, "moderate"),
    (0.5, "weak"),
)
# The columns of oni.ascii.txt: SEAS YR TOTAL ANOM.
ONI_COLUMNS = 4


def classify(anom: float) -> tuple[str, str]:
    """Return (phase, strength). The strength is empty for the neutral phase."""
    mag = abs(anom)
    for floor, strength in STRENGTH_FLOORS:
        if mag >= floor:
            return ("el_nino" if anom > 0 else "la_nina"), strength
    return "neutral", ""


def _oni_row(line: str) -> dict | None:
    """Return one row of oni.ascii.txt, or None for the header or a bad row."""
    parts = line.split()
    if len(parts) != ONI_COLUMNS:
        return None
    try:
        year, anom = int(parts[1]), float(parts[3])
    except ValueError:
        return None
    return (
        {"season": parts[0], "year": year, "anom": anom}
        if math.isfinite(anom)
        else None
    )


def build_enso(text: str) -> dict | None:
    """Return the last row of oni.ascii.txt as an ENSO dict, or None."""
    rows = [row for row in map(_oni_row, text.splitlines()) if row]
    if not rows:
        return None
    phase, strength = classify(rows[-1]["anom"])
    return {**rows[-1], "phase": phase, "strength": strength}


class EnsoCache:
    """Get the ONI one time each 24 hours.

    If a request fails, keep the last value and try again after RETRY_SECONDS.
    """

    def __init__(self, logger=None) -> None:
        self.value: dict | None = None
        self._fetched_at: float | None = None
        self._max_age: float = CACHE_SECONDS
        self._logger = logger

    async def get(self, session) -> dict | None:
        """Return the cached ENSO dict.

        Download the ONI file again when the cache is too old.
        """
        now = time.monotonic()
        if self._fetched_at is not None and now - self._fetched_at < self._max_age:
            return self.value
        # Set this before the request. The other pollers do not start a second
        # request. A poll that the host stops keeps the short wait.
        self._fetched_at, self._max_age = now, RETRY_SECONDS
        try:
            await self._download(session)
        # ENSO is optional background data. No failure here can stop an alert.
        except Exception as e:  # noqa: BLE001
            if self._logger:
                self._logger.warning(f"The ONI request failed: {type(e).__name__}")
        return self.value

    async def _download(self, session) -> None:
        """Store the ONI data. A file with no usable row keeps the last value."""
        async with session.get(ONI_URL) as resp:
            resp.raise_for_status()
            parsed = build_enso(await resp.text())
        if parsed:
            self.value, self._max_age = parsed, CACHE_SECONDS
