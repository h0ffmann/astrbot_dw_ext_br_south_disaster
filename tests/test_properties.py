"""Property tests. The parsers must accept any JSON value without an exception."""

from __future__ import annotations

import math
import types

from hypothesis import given
from hypothesis import strategies as st

JSON = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats()
    | st.text(max_size=12)
    | st.sampled_from(["RS", "SC", "PR", "Alto", "Moderado", "Muito Alto"]),
    lambda children: (
        st.lists(children, max_size=3)
        | st.dictionaries(st.text(max_size=6), children, max_size=3)
    ),
    max_leaves=8,
)
TIME = st.sampled_from(["2026-10-25 08:30:00.000", "25/10/26 08:00", "", None])
ALERT = st.fixed_dictionaries(
    {
        "cod_alerta": JSON,
        "uf": st.sampled_from(["RS", "SC", "PR", "XX"]),
        "nivel": st.sampled_from(["Moderado", "Alto", "Muito Alto", "Baixo"]) | JSON,
        "status": st.just(1) | JSON,
        "evento": JSON,
        "municipio": JSON,
        "codibge": JSON,
        "latitude": JSON,
        "longitude": JSON,
        "ult_atualizacao": TIME | JSON,
        "datahoracriacao": TIME | JSON,
    }
)
GAUGE = st.fixed_dictionaries(
    {
        "uf": st.sampled_from(["RS", "SC", "PR"]),
        "codibge": st.integers(0, 3) | JSON,
        "cidade": JSON,
        "nomeestacao": JSON,
        "acc1hr": st.floats() | JSON,
        "acc24hr": st.floats() | JSON,
        "datahoraUltimovalor": TIME | JSON,
    }
)
ROWS = st.lists(ALERT | JSON, max_size=5)
LIMIT = st.floats(0, 1000, allow_nan=False)


@given(JSON)
def test_parse_alerts_accepts_any_json(ext, data):
    """Check any top-level value."""
    assert isinstance(ext.extension.parse_alerts(data), list)


@given(JSON)
def test_parse_rain_accepts_any_json(ext, data):
    """Check any top-level value."""
    assert isinstance(ext.extension.parse_rain(data, uf="RS"), list)


@given(ROWS, st.text(max_size=24) | st.none())
def test_active_alerts_give_a_message(ext, make_api, rows, feed_time):
    """Check that each active alert gives an envelope and a text."""
    api = make_api("en")
    present = ext.presenter.make_presenter(api).present
    for alert in ext.extension.parse_alerts({"alertas": rows, "atualizado": feed_time}):
        assert alert["level"] in (2, 3, 4)
        if alert["active"]:
            event = ext.extension.build_alert_envelope(api, alert, None).event
            assert present(types.SimpleNamespace(**vars_of(event)))


def vars_of(event):
    """Return the fields of the presenter context."""
    return {
        "title": event.title,
        "headline": event.headline,
        "metadata": event.metadata,
    }


@given(st.lists(GAUGE | JSON, max_size=6), st.sampled_from(["RS", "SC", "PR"]))
def test_rain_items_are_unique_and_give_a_message(ext, make_api, gauges, uf):
    """Check that each municipality has one item and that each item gives a text."""
    api = make_api("en")
    present = ext.presenter.make_presenter(api).present
    items = ext.extension.parse_rain(gauges, ext.extension.DEFAULT_THRESHOLDS, uf)
    codes = [item["codibge"] for item in items]
    assert len(codes) == len(set(codes))
    for item in items:
        assert item["level"] in (2, 3, 4)
        event = ext.extension.build_rain_envelope(api, item, "20261025", None).event
        assert present(types.SimpleNamespace(**vars_of(event)))


@given(JSON)
def test_thresholds_are_always_usable(ext, value):
    """Check that the result has three levels of finite, positive limits."""
    thresholds = ext.extension.load_thresholds({"rain_thresholds": value})
    assert sorted(thresholds) == [2, 3, 4]
    assert all(
        math.isfinite(limit) and limit >= 0
        for pair in thresholds.values()
        for limit in pair
    )


@given(st.dictionaries(st.sampled_from(["yellow", "orange", "red"]), JSON, max_size=3))
def test_threshold_items_are_always_usable(ext, value):
    """Check values at the level of each key."""
    assert sorted(ext.extension.load_thresholds({"rain_thresholds": value})) == [
        2,
        3,
        4,
    ]


@given(JSON)
def test_selected_states_are_known(ext, value):
    """Check that the result has only known states."""
    assert set(ext.states.selected_states({"states": value})) <= set(ext.states.STATES)


@given(st.text(max_size=200))
def test_oni_parser_accepts_any_text(ext, text):
    """Check that a result has a finite anomaly."""
    enso = ext.enso.build_enso(text)
    assert enso is None or math.isfinite(enso["anom"])


@given(st.floats(-5, 5, allow_nan=False))
def test_el_nino_and_la_nina_have_the_same_bands(ext, anom):
    """Check that the sign changes only the phase."""
    classify = ext.enso.classify
    assert classify(anom)[1] == classify(-anom)[1]


@given(LIMIT, LIMIT, LIMIT, LIMIT)
def test_more_rain_never_lowers_the_level(ext, acc1, acc24, more1, more24):
    """Check that the level does not go down when a total goes up."""
    level = ext.extension.rain_level
    limits = ext.extension.DEFAULT_THRESHOLDS
    assert level(acc1 + more1, acc24 + more24, limits) >= level(acc1, acc24, limits)


@given(st.lists(st.integers(0, 3), max_size=8))
def test_alert_state_sends_each_alert_once(ext, ids):
    """Check that a second call with the same alerts returns nothing."""
    state = ext.extension.AlertState()
    alerts = [{"cod_alerta": i, "updated": "t"} for i in ids]
    assert len(state.fresh(alerts)) == len(set(ids))
    assert state.fresh(alerts) == []
