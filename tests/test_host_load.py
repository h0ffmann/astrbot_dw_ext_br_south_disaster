"""Load the extension offline with the real extension manager of the host."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from astrbot_plugin_disaster_warning.core.extensions.host_registry import HostRegistry
from astrbot_plugin_disaster_warning.core.extensions.manager import ExtensionManager
from test_hardening import FEED_TIME, Session, alert_row, gauge_row

EXT_DIR = Path(__file__).resolve().parents[1]
ID = "br_south_disaster"


class FakeService:
    """The part of the host service that the extension manager uses."""

    def __init__(self, settings):
        self.config = {
            "extensions": {"enabled_ids": [ID], "settings": json.dumps({ID: settings})}
        }


@pytest.fixture
def load(tmp_path):
    """Return a function that loads the extension. Remove the registrations at the end."""
    root = tmp_path / "extensions"
    root.mkdir()
    (root / ID).symlink_to(EXT_DIR, target_is_directory=True)

    def _load(settings):
        manager = ExtensionManager(
            FakeService(settings), HostRegistry(), roots=[root], data_dir=tmp_path
        )
        manager.load_all()
        return manager

    yield _load
    HostRegistry().unregister_source_entries(owner=ID)
    HostRegistry().unregister_presenters(owner=ID)


def test_extension_loads_in_the_host(load):
    """Check the manifest, the relative imports and the registrations."""
    (record,) = load({"language": "en"}).status()
    assert record["state"] == "loaded", record["error"]
    assert sorted(record["sources"]) == [
        f"{ID}_cemaden_alerts",
        f"{ID}_cemaden_rain",
    ]


def test_directory_with_the_repository_name_does_not_load(tmp_path):
    """Check the rule that the installation procedure tells the operator to obey."""
    root = tmp_path / "extensions"
    root.mkdir()
    (root / "astrbot_dw_ext_br_south_disaster").symlink_to(EXT_DIR)
    manager = ExtensionManager(
        FakeService({}), HostRegistry(), roots=[root], data_dir=tmp_path
    )
    manager.load_all()
    assert not manager._apis


def test_host_applies_the_lower_limit_of_the_interval(load):
    """Check that a small interval does not send a request each second."""
    api = load({"alerts_interval": 0, "rain_interval": -5})._apis[ID]
    assert {spec.interval_seconds for spec in api.pollers} == {api.MIN_INTERVAL_SECONDS}


def test_bad_settings_do_not_stop_the_load(load):
    """Check the settings that stopped the setup in earlier versions."""
    (record,) = load(
        {"rain_thresholds": "high", "alerts_interval": 1e999, "states": "SC"}
    ).status()
    assert record["state"] == "loaded", record["error"]


def test_each_poller_gives_real_host_envelopes(load):
    """Check the pollers against the real models of the host."""
    api = load({"language": "en", "states": ["SC"]})._apis[ID]
    session = Session(
        wsAlertas2=json.dumps({"atualizado": FEED_TIME, "alertas": [alert_row()]}),
        getJson2=json.dumps([gauge_row()]),
        oni=RuntimeError("no ENSO"),
    )
    envelopes = [
        asyncio.run(spec.fetch(session))[0] for spec in sorted_pollers(api.pollers)
    ]
    assert [env.identity.event_id for env in envelopes] == [
        f"{ID}_cemaden_1",
        f"{ID}_rain_4205407_{envelopes[1].identity.event_id.split('_')[-2]}_2",
    ]


def sorted_pollers(pollers):
    """Return the alert poller first."""
    return sorted(pollers, key=lambda spec: spec.source_id)
