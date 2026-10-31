"""The pollers of the extension. The host calls each poller with an HTTP session."""

from __future__ import annotations

import json
from datetime import datetime

from .cemaden import ALERTS_URL, BRT, RAIN_URL, parse_alerts, parse_rain
from .envelopes import build_alert_envelope, build_rain_envelope


class FeedFormatError(Exception):
    """A feed sent a JSON value of an unexpected type."""


async def _get_json(session, url: str, expected: type):
    """Return the JSON of url. Raise FeedFormatError for an unexpected top-level type.

    The host logs the error. Thus, a changed feed does not look like an empty feed.
    """
    async with session.get(url) as resp:
        resp.raise_for_status()
        data = json.loads(await resp.text())  # The server sends JSON as text/html.
    if not isinstance(data, expected):
        raise FeedFormatError(url)
    return data


class AlertPoller:
    """Return the envelopes of the new or updated alerts of the selected states."""

    def __init__(self, api, ufs: tuple[str, ...], enso, state) -> None:
        self._api, self._ufs, self._enso, self._state = api, ufs, enso, state

    async def __call__(self, session) -> list:
        """Read the feed and return the envelopes."""
        data = await _get_json(session, ALERTS_URL, dict)
        alerts = [a for a in parse_alerts(data, self._ufs) if a["active"]]
        if not alerts:
            return []
        # Get ENSO before the state changes. A timeout then does not lose an alert.
        ctx = await self._enso.get(session)
        fresh = self._state.fresh(alerts)
        return [build_alert_envelope(self._api, a, ctx) for a in fresh]


class RainPoller:
    """Return the envelopes of the rain levels that increased in one state."""

    def __init__(self, api, uf: str, thresholds: dict, enso, state) -> None:
        self._api, self._uf, self._thresholds = api, uf, thresholds
        self._enso, self._state = enso, state

    async def __call__(self, session) -> list:
        """Read the feed and return the envelopes."""
        gauges = await _get_json(session, RAIN_URL.format(uf=self._uf), list)
        day = datetime.now(BRT).strftime("%Y%m%d")
        items = parse_rain(gauges, self._thresholds, self._uf)
        if not items:
            return []
        ctx = await self._enso.get(session)
        fresh = self._state.escalations(items, day)
        return [build_rain_envelope(self._api, i, day, ctx) for i in fresh]
