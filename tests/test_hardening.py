"""Regression tests for feeds and settings with unexpected values."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import types
from datetime import datetime, timezone

import pytest

FEED_TIME = "25-10-2026 12:00:00 UTC"


def alert_row(**changes):
    """Return a valid alert row of the CEMADEN feed."""
    row = {
        "cod_alerta": 1,
        "uf": "SC",
        "nivel": "Alto",
        "evento": "Risco Hidrologico - Alto",
        "status": 1,
        "codibge": 4205407,
        "municipio": "Florianopolis",
        "datahoracriacao": "2026-10-25 08:00:00.000",
        "ult_atualizacao": "2026-10-25 08:30:00.000",
    }
    return {**row, **changes}


def gauge_row(**changes):
    """Return a valid rain gauge row of the CEMADEN feed."""
    row = {
        "uf": "SC",
        "codibge": 4205407,
        "cidade": "Florianopolis",
        "nomeestacao": "Centro",
        "acc1hr": 25.0,
        "acc24hr": 60.0,
        "datahoraUltimovalor": "25/10/26 08:00",
    }
    return {**row, **changes}


class _Response:
    def __init__(self, body):
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    def raise_for_status(self):
        if isinstance(self._body, Exception):
            raise self._body

    async def text(self):
        return self._body


class Session:
    """Fake aiohttp session. Each URL fragment gives a text or an exception."""

    def __init__(self, **routes):
        self.routes = routes
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        for fragment, body in self.routes.items():
            if fragment in url:
                return _Response(body)
        return _Response(RuntimeError(url))


def run(coro):
    """Run a coroutine."""
    return asyncio.run(coro)


def alerts_poller(ext, make_api, config=None):
    """Return the alert poller of a new extension."""
    api = make_api("en", config or {"states": ["SC"]})
    ext.extension.setup(api)
    return api.all_pollers[0][1]


# ---------------------------------------------------------------- feeds


@pytest.mark.parametrize("data", [None, [], "text", 3, {}, {"alertas": "text"}])
def test_alerts_feed_of_a_wrong_type_has_no_alerts(ext, data):
    """Check that the parser accepts any top-level value."""
    assert ext.extension.parse_alerts(data) == []


@pytest.mark.parametrize(
    "bad",
    [
        1,
        "text",
        None,
        [],
        {},
        alert_row(nivel=["Alto"]),
        alert_row(cod_alerta=None),
        alert_row(cod_alerta=""),
        alert_row(cod_alerta=True),
        alert_row(cod_alerta=[1]),
    ],
)
def test_bad_alert_row_does_not_stop_the_good_row(ext, bad):
    """Check that the parser skips only the row that it cannot use."""
    data = {"atualizado": FEED_TIME, "alertas": [bad, alert_row(cod_alerta=7)]}
    assert [a["cod_alerta"] for a in ext.extension.parse_alerts(data)] == [7]


def test_alert_event_that_is_not_text_is_a_flood(ext):
    """Check the default hazard."""
    data = {"atualizado": FEED_TIME, "alertas": [alert_row(evento=5)]}
    assert ext.extension.parse_alerts(data)[0]["hazard"] == "flood"


@pytest.mark.parametrize("gauges", [None, {}, "text", 3, [1, "x", None, []]])
def test_rain_feed_of_a_wrong_type_has_no_items(ext, gauges):
    """Check that the parser accepts any value."""
    assert ext.extension.parse_rain(gauges, uf="SC") == []


def test_gauges_with_no_code_are_not_one_municipality(ext):
    """Check that the parser does not join gauges with no municipality code."""
    gauges = [gauge_row(codibge=None), gauge_row(codibge=""), gauge_row(codibge=True)]
    assert ext.extension.parse_rain(gauges, uf="SC") == []


@pytest.mark.parametrize("value", [True, math.nan, math.inf, "-", None, [1]])
def test_rain_total_that_is_not_a_number_is_ignored(ext, value):
    """Check that only real numbers can start a rain alert."""
    gauges = [gauge_row(acc1hr=value, acc24hr=value)]
    assert ext.extension.parse_rain(gauges, uf="SC") == []


def test_alert_poller_skips_a_bad_row(ext, make_api):
    """Check the full poller with one bad row."""
    feed = {"atualizado": FEED_TIME, "alertas": [{"uf": 1}, 2, alert_row()]}
    session = Session(wsAlertas2=json.dumps(feed), oni=RuntimeError("no ENSO"))
    envelopes = run(alerts_poller(ext, make_api)(session))
    assert len(envelopes) == 1


@pytest.mark.parametrize("body", ["[]", "null", "3", '"text"'])
def test_alert_poller_reports_a_changed_feed(ext, make_api, body):
    """Check that a changed feed gives an error and not an empty result."""
    with pytest.raises(ext.extension.FeedFormatError):
        run(alerts_poller(ext, make_api)(Session(wsAlertas2=body)))


@pytest.mark.parametrize("body", ["{}", "null", "3"])
def test_rain_poller_reports_a_changed_feed(ext, make_api, body):
    """Check that a changed feed gives an error and not an empty result."""
    api = make_api("en", {"states": ["SC"]})
    ext.extension.setup(api)
    with pytest.raises(ext.extension.FeedFormatError):
        run(api.all_pollers[1][1](Session(getJson2=body)))


def test_failed_request_keeps_the_alert_for_the_next_poll(ext, make_api):
    """Check that a failed poll does not mark an alert as sent."""
    fetch = alerts_poller(ext, make_api)
    with pytest.raises(ValueError):
        run(fetch(Session(wsAlertas2="not json")))
    feed = json.dumps({"atualizado": FEED_TIME, "alertas": [alert_row()]})
    session = Session(wsAlertas2=feed, oni=RuntimeError("no ENSO"))
    assert len(run(fetch(session))) == 1
    assert run(fetch(session)) == []


def test_rain_state_starts_again_on_a_new_day(ext):
    """Check that the same level gives a new message on the next day."""
    state, item = ext.extension.RainState(), {"codibge": 1, "level": 3}
    assert state.escalations([item], "20261025") == [item]
    assert state.escalations([item], "20261025") == []
    assert state.escalations([item], "20261026") == [item]


def test_gauge_time_is_utc_and_the_message_uses_brasilia_time(ext, make_api):
    """Check that 03:30 in the feed is 03:30 UTC and that the message shows 00:30."""
    api = make_api("en")
    (item,) = ext.extension.parse_rain(
        [gauge_row(datahoraUltimovalor="31/10/26 03:30")], uf="SC"
    )
    assert item["observed_at"] == datetime(2026, 10, 31, 3, 30, tzinfo=timezone.utc)
    env = ext.extension.build_rain_envelope(api, item, "20261031", None)
    assert env.event.metadata["issue_time"] == "2026-10-31T00:30:00-03:00"
    context = types.SimpleNamespace(
        title=env.event.title, headline=env.event.headline, metadata=env.event.metadata
    )
    text = ext.presenter.make_presenter(api).present(context)
    assert "31/10/2026 00:30 (Brasília time)" in text


def test_gauge_time_can_be_on_the_day_before_in_brasilia(ext):
    """Check a reading just after midnight UTC."""
    (item,) = ext.extension.parse_rain(
        [gauge_row(datahoraUltimovalor="01/11/26 01:00")], uf="SC"
    )
    assert item["observed_at"].strftime("%d/%m %H:%M") == "31/10 22:00"


# ------------------------------------------------------------- settings


@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan, True, "a", None, []])
def test_interval_that_is_not_a_number_uses_the_default(ext, make_api, value, caplog):
    """Check that the setup logs a warning and uses the default."""
    api = make_api("en", {"alerts_interval": value})
    with caplog.at_level(logging.WARNING):
        ext.extension.setup(api)
    assert api.all_pollers[0][2] == 300
    assert "alerts_interval" in caplog.text


def test_bad_rain_interval_logs_one_warning(ext, make_api, caplog):
    """Check that the setup does not repeat the warning for each state."""
    with caplog.at_level(logging.WARNING):
        ext.extension.setup(make_api("en", {"rain_interval": "a"}))
    assert caplog.text.count("rain_interval") == 1


@pytest.mark.parametrize("value", ["text", 3, [], True, None])
def test_thresholds_that_are_not_an_object_use_the_defaults(ext, make_api, value):
    """Check that a bad value does not stop the setup."""
    config = {"rain_thresholds": value}
    assert ext.extension.load_thresholds(config) == ext.extension.DEFAULT_THRESHOLDS
    ext.extension.setup(make_api("en", config))


@pytest.mark.parametrize("value", [-1, math.inf, math.nan, True, "a", None, []])
def test_bad_limit_keeps_the_default_of_the_level(ext, value):
    """Check that one bad limit changes no value of that level."""
    config = {"rain_thresholds": {"red": {"acc1hr": 1, "acc24hr": value}}}
    assert ext.extension.load_thresholds(config) == ext.extension.DEFAULT_THRESHOLDS


def test_good_limit_changes_only_that_value(ext):
    """Check a partial setting."""
    config = {"rain_thresholds": {"red": {"acc24hr": "120"}, "blue": {"acc1hr": 1}}}
    expected = {**ext.extension.DEFAULT_THRESHOLDS, 4: (60.0, 120.0)}
    assert ext.extension.load_thresholds(config) == expected


def test_states_that_are_not_a_list_log_a_warning(ext, make_api, caplog):
    """Check that the setup tells the operator about this mistake."""
    api = make_api("en", {"states": "SC"})
    with caplog.at_level(logging.WARNING):
        ext.extension.setup(api)
    assert len(api.all_pollers) == 4
    assert "not a list" in caplog.text


# ----------------------------------------------------------------- ENSO

ONI = "SEAS YR TOTAL ANOM\nASO 2026 28.1 1.2\n"


def test_failed_enso_request_retries_after_one_hour(ext, oni_text):
    """Check that one failure does not stop the ENSO data for 24 hours."""
    cache = ext.enso.EnsoCache()
    failed = Session(oni=RuntimeError("down"))
    assert run(cache.get(failed)) is None
    assert run(cache.get(failed)) is None
    assert len(failed.calls) == 1
    cache._fetched_at -= ext.enso.RETRY_SECONDS + 1
    assert run(cache.get(Session(oni=oni_text))) is not None


def test_enso_success_keeps_the_24_hour_cache(ext):
    """Check that a good request does not use the short wait."""
    cache = ext.enso.EnsoCache()
    run(cache.get(Session(oni=ONI)))
    cache._fetched_at -= ext.enso.RETRY_SECONDS + 1
    session = Session(oni=ONI)
    run(cache.get(session))
    assert session.calls == []


def test_failed_enso_refresh_keeps_the_last_value(ext):
    """Check that the cache keeps old data if a new request fails."""
    cache = ext.enso.EnsoCache()
    value = run(cache.get(Session(oni=ONI)))
    cache._fetched_at -= ext.enso.CACHE_SECONDS + 1
    assert run(cache.get(Session(oni=RuntimeError("down")))) == value


def test_enso_failure_goes_to_the_log(ext, caplog):
    """Check that a failed request is not silent."""
    cache = ext.enso.EnsoCache(logging.getLogger("enso.test"))
    with caplog.at_level(logging.WARNING):
        run(cache.get(Session(oni=RuntimeError("down"))))
    assert "RuntimeError" in caplog.text


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_enso_ignores_a_row_with_no_real_anomaly(ext, value):
    """Check that the parser keeps the last usable row."""
    enso = ext.enso.build_enso(f"{ONI}SON 2026 28.1 {value}\n")
    assert (enso["season"], enso["anom"]) == ("ASO", 1.2)


# ------------------------------------------------------------ presenter


@pytest.mark.parametrize("value", [123, "not a date"])
def test_presenter_shows_a_bad_time_as_text(ext, make_api, value):
    """Check that a bad time does not stop the message."""
    presenter = ext.presenter.make_presenter(make_api("en"))
    context = types.SimpleNamespace(
        title="Title",
        headline="",
        metadata={"hazard": "rain", "issue_time": value, "severity_level": 2},
    )
    assert str(value) in presenter.present(context)
