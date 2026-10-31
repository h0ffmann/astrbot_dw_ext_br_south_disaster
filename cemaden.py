"""CEMADEN feeds: the URLs, the constants and the parsers.

An alert is active if CEMADEN gives status 1 and the last update is MAX_AGE_DAYS
old or newer. The extension does not send past alerts.

The feeds can change without notice. A parser skips a row that it cannot use.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from .states import STATES

ALERTS_URL = "https://painelalertas.cemaden.gov.br/wsAlertas2"
RAIN_URL = "https://resources.cemaden.gov.br/graficos/interativo/getJson2.php?uf={uf}"

BRT = timezone(timedelta(hours=-3))  # Brasília time, no daylight saving time
ALERT_LEVELS = {"Moderado": 2, "Alto": 3, "Muito Alto": 4}
DEFAULT_THRESHOLDS = {  # level -> (acc1hr mm, acc24hr mm)
    2: (20.0, 50.0),
    3: (30.0, 100.0),
    4: (60.0, 150.0),
}
ALERT_TIME_FMT = "%Y-%m-%d %H:%M:%S"
FEED_TIME_FMT = "%d-%m-%Y %H:%M:%S UTC"  # The atualizado field, in UTC
ACTIVE_STATUS = 1
MAX_AGE_DAYS = 90  # Hard limit. An alert with an older last update is past, not active.
GAUGE_TIME_FMT = "%d/%m/%y %H:%M"


def _parse_time(text, fmt: str) -> datetime | None:
    try:
        return datetime.strptime(text, fmt).replace(tzinfo=BRT)
    except (TypeError, ValueError):  # strptime() needs str. Other types give TypeError.
        return None


def _feed_time(data: dict) -> datetime:
    """Return the time of the list (atualizado), or the time now if it is not valid."""
    try:
        return datetime.strptime(data["atualizado"], FEED_TIME_FMT).replace(
            tzinfo=timezone.utc
        )
    except (KeyError, TypeError, ValueError):
        return datetime.now(timezone.utc)


def is_active(raw: dict, updated_at: datetime | None, feed_time: datetime) -> bool:
    """Return True for status 1 and a last update MAX_AGE_DAYS old or newer."""
    return (
        raw.get("status") == ACTIVE_STATUS
        and updated_at is not None
        and feed_time - updated_at <= timedelta(days=MAX_AGE_DAYS)
    )


def _rows(value) -> list[dict]:
    """Return the dict items of a feed list."""
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _valid_id(value) -> bool:
    """Return True for a value that can identify an alert or a municipality."""
    return isinstance(value, (int, str)) and not isinstance(value, bool) and value != ""


def _alert_level(raw: dict) -> int | None:
    level = raw.get("nivel")
    return ALERT_LEVELS.get(level) if isinstance(level, str) else None


def _hazard(raw: dict) -> str:
    event = raw.get("evento")
    if isinstance(event, str) and event.startswith("Movimentos de Massa"):
        return "landslide"
    return "flood"


def _alert_item(raw: dict, level: int, feed_time: datetime) -> dict:
    updated_at = _parse_time(str(raw.get("ult_atualizacao"))[:19], ALERT_TIME_FMT)
    return {
        "raw": raw,
        "cod_alerta": raw.get("cod_alerta"),
        "level": level,
        "hazard": _hazard(raw),
        "issued_at": _parse_time(str(raw.get("datahoracriacao"))[:19], ALERT_TIME_FMT),
        # An alert stays active for days.
        # The host time rule must use the last update.
        "updated_at": updated_at,
        "updated": raw.get("ult_atualizacao") or "",
        "active": is_active(raw, updated_at, feed_time),
    }


def parse_alerts(data: dict, ufs=tuple(STATES)) -> list[dict]:
    """Keep the alerts of the states in ufs that have a known level and an id.

    Add the hazard, the times and the active flag.
    """
    data = data if isinstance(data, dict) else {}
    feed_time = _feed_time(data)
    out = []
    for raw in _rows(data.get("alertas")):
        level = _alert_level(raw)
        if raw.get("uf") in ufs and level and _valid_id(raw.get("cod_alerta")):
            out.append(_alert_item(raw, level, feed_time))
    return out


def _num(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None  # "-" -> None
    return float(value) if math.isfinite(value) else None


def _meets(value: float | None, limit: float) -> bool:
    return value is not None and value >= limit


def rain_level(acc1: float | None, acc24: float | None, thresholds: dict) -> int:
    """Return the highest level that the 1 h or the 24 h total meets, or 0."""
    return max(
        (
            lvl
            for lvl, (t1, t24) in thresholds.items()
            if _meets(acc1, t1) or _meets(acc24, t24)
        ),
        default=0,
    )


def _gauge_item(g: dict, thresholds: dict) -> dict | None:
    """Return the rain item of one gauge, or None if the gauge meets no threshold."""
    acc1, acc24 = _num(g.get("acc1hr")), _num(g.get("acc24hr"))
    level = rain_level(acc1, acc24, thresholds)
    if not level:
        return None
    return {
        "rank": (level, acc24 or 0.0, acc1 or 0.0),
        "uf": g.get("uf"),
        "codibge": g.get("codibge"),
        "municipio": g.get("cidade") or "",
        "station": g.get("nomeestacao") or "",
        "level": level,
        "acc1hr": acc1,
        "acc24hr": acc24,
        "observed_at": _parse_time(g.get("datahoraUltimovalor"), GAUGE_TIME_FMT),
    }


def parse_rain(
    gauges: list, thresholds: dict = DEFAULT_THRESHOLDS, uf: str = "RS"
) -> list[dict]:
    """Keep the worst active gauge of each municipality in the state uf.

    Keep only the gauges that meet a threshold. A gauge is past if its last reading
    is more than MAX_AGE_DAYS older than the newest reading of the list.
    """
    rows = _rows(gauges)
    items = [
        _gauge_item(g, thresholds)
        for g in rows
        if g.get("uf") == uf and _valid_id(g.get("codibge"))
    ]
    newest = _newest_reading(rows)
    worst: dict = {}
    for item in items:
        if item is None or not _recent(item["observed_at"], newest):
            continue
        code = item["codibge"]
        if code not in worst or item["rank"] > worst[code]["rank"]:
            worst[code] = item
    return list(worst.values())


def _newest_reading(gauges: list[dict]) -> datetime | None:
    times = (_parse_time(g.get("datahoraUltimovalor"), GAUGE_TIME_FMT) for g in gauges)
    return max((t for t in times if t), default=None)


def _recent(when: datetime | None, newest: datetime | None) -> bool:
    if when is None or newest is None:
        return False
    return newest - when <= timedelta(days=MAX_AGE_DAYS)
