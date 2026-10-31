"""South of Brazil (RS, SC, PR): CEMADEN alerts, CEMADEN rain gauges, and ENSO data.

The states are in states.py. To add a state, add one line there.
The setting "states" selects some of the states. The default is all states.
This module has the entry point. See pollers.py and cemaden.py for the other code.
"""

from __future__ import annotations

from .cemaden import (
    ALERTS_URL,
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
from .pollers import AlertPoller, FeedFormatError, RainPoller
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
    thresholds = load_thresholds(cfg)
    rain_state = RainState()

    api.register_presenter(PRESENTER_KEY, make_presenter(api))
    api.register_source(source_entry(api, ALERTS_SOURCE, "alerts", 2))
    api.register_source(source_entry(api, RAIN_SOURCE, "rain", 1))
    api.register_poller(
        ALERTS_SOURCE,
        AlertPoller(api, ufs, enso, AlertState()),
        interval_seconds=int_setting(api, cfg, "alerts_interval", 300),
    )
    rain_interval = int_setting(api, cfg, "rain_interval", 300)
    for uf in ufs:
        api.register_poller(
            RAIN_SOURCE,
            RainPoller(api, uf, thresholds, enso, rain_state),
            interval_seconds=rain_interval,
        )
