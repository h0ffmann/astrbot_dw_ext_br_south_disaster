"""Read the settings of the extension. A bad value does not stop the setup."""

from __future__ import annotations

import math

from .cemaden import DEFAULT_THRESHOLDS

LEVEL_KEYS = {2: "yellow", 3: "orange", 4: "red"}


def int_setting(api, cfg: dict, key: str, default: int) -> int:
    """Return cfg[key] as an int.

    If the value is not a finite number, log a warning and return the default.
    """
    value = cfg.get(key, default)
    try:
        if not isinstance(value, bool):
            return int(value)
    except (TypeError, ValueError, OverflowError):
        pass
    api.logger.warning(f"Setting '{key}' is not a number. Use {default}.")
    return default


def _threshold(value) -> float:
    """Return a limit in mm. Raise ValueError if the value is not usable."""
    limit = float(value)
    if isinstance(value, bool) or not math.isfinite(limit) or limit < 0:
        raise ValueError(value)
    return limit


def load_thresholds(config: dict) -> dict:
    """Replace the default thresholds with the values in config["rain_thresholds"].

    A level with a value that is not usable keeps its default thresholds.
    """
    merged = dict(DEFAULT_THRESHOLDS)
    custom = (config or {}).get("rain_thresholds")
    if not isinstance(custom, dict):
        return merged
    for lvl, key in LEVEL_KEYS.items():
        item = custom.get(key)
        if isinstance(item, dict):
            t1, t24 = merged[lvl]
            try:
                merged[lvl] = (
                    _threshold(item.get("acc1hr", t1)),
                    _threshold(item.get("acc24hr", t24)),
                )
            except (TypeError, ValueError, OverflowError):
                continue  # Keep the default threshold
    return merged
