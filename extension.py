"""South of Brazil (RS, SC, PR): CEMADEN alerts, CEMADEN rain gauges, and ENSO data.

The states are in states.py. To add a state, add one line there.
The setting "states" selects some of the states. The default is all states.
This module has the entry point and the pollers. See cemaden.py for the parsers.
"""

from __future__ import annotations

import json
from datetime import datetime

from .cemaden import (
    ALERTS_URL,
    BRT,
    DEFAULT_THRESHOLDS,
    GAUGE_TIME_FMT,
    RAIN_URL,
    _parse_time,
    parse_alerts,
    parse_rain,
    rain_level,
)
from .enso import EnsoCache
from .envelopes import (
    ALERTS_SOURCE,
    PRESENTER_KEY,
    RAIN_SOURCE,
    build_alert_envelope,
    build_rain_envelope,
    source_entry,
)
from .presenter import make_presenter
from .settings import int_setting, load_thresholds
from .states import STATES, selected_states
from .tracking import AlertState, RainState

__all__ = [
    "ALERTS_URL",
    "DEFAULT_THRESHOLDS",
    "GAUGE_TIME_FMT",
    "RAIN_URL",
    "AlertState",
    "FeedFormatError",
    "RainState",
    "_parse_time",
    "build_alert_envelope",
    "build_rain_envelope",
    "int_setting",
    "load_thresholds",
    "parse_alerts",
    "parse_rain",
    "rain_level",
    "setup",
]


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


def _states(api, cfg: dict) -> tuple[str, ...]:
    """Return the selected states. Log a warning if the setting is not usable."""
    ufs = selected_states(cfg)
    if not ufs:
        api.logger.warning(
            f"No known state in 'states'. Use all states {list(STATES)}."
        )
        return tuple(STATES)
    if cfg.get("states") and not isinstance(cfg["states"], (list, tuple)):
        api.logger.warning("Setting 'states' is not a list. Use all states.")
    return ufs


def setup(api) -> None:
    """Entry point of the extension.

    Register the presenter and the two sources. Register one alert poller,
    and one rain poller for each selected state. An error in one state does not stop
    the pollers of the other states.
    """
    cfg = api.config or {}
    ufs = _states(api, cfg)
    enso = EnsoCache(api.logger)
    alert_state, rain_state = AlertState(), RainState()
    thresholds = load_thresholds(cfg)

    async def fetch_alerts(session):
        alerts = parse_alerts(await _get_json(session, ALERTS_URL, dict), ufs)
        alerts = [a for a in alerts if a["active"]]
        if not alerts:
            return []
        # Get ENSO before the state changes. A timeout then does not lose an alert.
        ctx = await enso.get(session)
        alerts = alert_state.fresh(alerts)
        return [build_alert_envelope(api, a, ctx) for a in alerts]

    def rain_fetcher(uf: str):
        async def fetch_rain(session):
            gauges = await _get_json(session, RAIN_URL.format(uf=uf), list)
            day = datetime.now(BRT).strftime("%Y%m%d")
            items = parse_rain(gauges, thresholds, uf)
            if not items:
                return []
            ctx = await enso.get(session)
            items = rain_state.escalations(items, day)
            return [build_rain_envelope(api, i, day, ctx) for i in items]

        return fetch_rain

    api.register_presenter(PRESENTER_KEY, make_presenter(api))
    api.register_source(source_entry(api, ALERTS_SOURCE, "alerts", 2))
    api.register_source(source_entry(api, RAIN_SOURCE, "rain", 1))
    api.register_poller(
        ALERTS_SOURCE,
        fetch_alerts,
        interval_seconds=int_setting(api, cfg, "alerts_interval", 300),
    )
    rain_interval = int_setting(api, cfg, "rain_interval", 300)
    for uf in ufs:
        api.register_poller(
            RAIN_SOURCE, rain_fetcher(uf), interval_seconds=rain_interval
        )
