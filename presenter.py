"""Text presenter for the br_south_disaster weather events."""

from __future__ import annotations

from datetime import datetime

EMOJI = {0: "⚪", 1: "🔵", 2: "🟡", 3: "🟠", 4: "🔴"}
ENSO_PHASES = ("el_nino", "la_nina")  # The neutral phase has no text.


def make_presenter(api):
    """Return a presenter class that is bound to the translator of the extension."""

    class BrSouthWeatherPresenter:
        """Text presenter for the alerts and the rain events of br_south_disaster."""

        @classmethod
        def present(cls, display_context, _options=None) -> str:
            """Return the message text for a weather display context."""
            return render(api.t, display_context)

    return BrSouthWeatherPresenter


def render(t, context) -> str:
    """Return the message text. The function t translates a key."""
    md = context.metadata or {}
    level = int(md.get("severity_level") or 0)
    enso_line = _enso_line(t, md.get("enso") or {})
    sources = "CEMADEN / NOAA CPC" if enso_line else "CEMADEN"
    lines = [
        f"{EMOJI.get(level, '⚪')} {context.title}",
        context.headline,
        _detail_line(t, md),
        _time_line(t, md),
        enso_line,
        t("present.source", sources=sources),
    ]
    return "\n".join(line for line in lines if line)


def _detail_line(t, md: dict) -> str:
    """Return the rain totals or the hazard. An event with neither has no line."""
    if md.get("hazard") == "rain":
        dec = t("format.decimal")
        return t(
            "present.rain",
            acc1hr=_mm(md.get("acc1hr"), dec),
            acc24hr=_mm(md.get("acc24hr"), dec),
        )
    if md.get("hazard"):
        return t("present.hazard", hazard=t(f"hazard.{md['hazard']}"))
    return ""


def _time_line(t, md: dict) -> str:
    """Return the line with the time of the event, if the event has a time."""
    when = _fmt_time(md.get("issue_time"), t("format.time"))
    return t("present.time", time=when) if when else ""


def _enso_line(t, enso: dict) -> str:
    """Return the background line for El Niño or La Niña."""
    if enso.get("phase") not in ENSO_PHASES:
        return ""
    return t(
        "present.enso",
        phase=t(f"enso.phase.{enso['phase']}"),
        strength=t(f"enso.strength.{enso['strength']}"),
        season=enso.get("season", ""),
        year=enso.get("year", ""),
        anom=f"{enso.get('anom', 0):+.2f}".replace(".", t("format.decimal")),
    )


def _mm(value, dec: str) -> str:
    """Return a rain total with the decimal mark of the language."""
    return "-" if value is None else f"{value:g}".replace(".", dec)


def _fmt_time(iso, fmt: str) -> str:
    """Return an ISO time in the format of the language."""
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime(fmt)
    except (TypeError, ValueError):
        return str(iso)
