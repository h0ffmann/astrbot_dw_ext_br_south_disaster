"""The state that stops repeated messages. The state is in memory.

After a restart, the startup silence and the time rule of the host stop old events.
"""

from __future__ import annotations


class AlertState:
    """Store the last update of each alert. Return only new or updated alerts."""

    def __init__(self) -> None:
        # ponytail: the dict keeps each alert id forever (a few KB a year).
        # Remove old ids if the memory use becomes a problem.
        self._seen: dict = {}

    def fresh(self, alerts: list[dict]) -> list[dict]:
        """Return the alerts that are new or have a newer update time."""
        out = []
        for a in alerts:
            if self._seen.get(a["cod_alerta"]) != a["updated"]:
                self._seen[a["cod_alerta"]] = a["updated"]
                out.append(a)
        return out


class RainState:
    """Store the last level of each municipality for the day.

    Return only higher levels.
    """

    def __init__(self) -> None:
        self._last: dict = {}

    def escalations(self, items: list[dict], day: str) -> list[dict]:
        """Return the items with a level higher than the last level of the day.

        The comparison uses the last level of the same municipality.
        """
        out = []
        for it in items:
            prev_day, prev_level = self._last.get(it["codibge"], (None, 0))
            if prev_day != day:
                prev_level = 0
            if it["level"] > prev_level:
                self._last[it["codibge"]] = (day, it["level"])
                out.append(it)
        return out
