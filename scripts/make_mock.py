"""Make a page that shows the messages of the extension in a mock chat.

The text is the real output of the extension, through the host loader and presenter.
Usage: make_mock.py <extensions_root> <output_file> [--offline]
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = Path(os.environ["DW_HOST_DIR"])
ID = "br_south_disaster"
LANGS = {
    "en": "English",
    "zh-CN": "简体中文",
    "pt-BR": "Português (Brasil)",
    "ja-JP": "日本語",
}
ALERTS = "https://painelalertas.cemaden.gov.br/wsAlertas2"
RAIN = "https://resources.cemaden.gov.br/graficos/interativo/getJson2.php?uf={uf}"
ONI = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
STATES = ("RS", "SC", "PR")


class _Response:
    def __init__(self, body):
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    def raise_for_status(self):
        return None

    async def text(self):
        return self._body


class ReplaySession:
    """Return the stored body of each URL."""

    def __init__(self, bodies):
        self._bodies = bodies

    def get(self, url):
        return _Response(self._bodies[url])


def load_host():
    """Add the AstrBot stubs and return the host names that this script uses."""
    path = HOST / "tests/conftest.py"
    spec = importlib.util.spec_from_file_location("_dw_host_bootstrap", path)
    spec.loader.exec_module(importlib.util.module_from_spec(spec))
    importlib.import_module("astrbot_plugin_disaster_warning.core.app.disaster_service")
    package = "astrbot_plugin_disaster_warning.core"
    manager = importlib.import_module(f"{package}.extensions.manager")
    registry = importlib.import_module(f"{package}.extensions.host_registry")
    presenters = importlib.import_module(
        f"{package}.message.presenters.presenter_registry"
    )
    return manager, registry.HostRegistry, presenters.present_message


def recorded_bodies() -> dict:
    """Return the recorded feeds in tests/fixtures."""
    fixtures = ROOT / "tests/fixtures"
    bodies = {
        ALERTS: (fixtures / "cemaden_alertas.json").read_text("utf-8"),
        ONI: (fixtures / "oni.ascii.txt").read_text("utf-8"),
    }
    for uf in STATES:
        path = fixtures / f"cemaden_rain_{uf}.json"
        bodies[RAIN.format(uf=uf)] = path.read_text("utf-8")
    return bodies


async def live_bodies(manager_module) -> dict | None:
    """Return the feeds now, or None if a request fails."""
    import aiohttp

    urls = [ALERTS, ONI, *(RAIN.format(uf=uf) for uf in STATES)]
    connector = aiohttp.TCPConnector(ssl=manager_module._build_ssl_context())
    headers = {"User-Agent": "Mozilla/5.0"}
    timeout = aiohttp.ClientTimeout(total=45)
    bodies = {}
    try:
        async with aiohttp.ClientSession(
            connector=connector, headers=headers, timeout=timeout
        ) as session:
            for url in urls:
                async with session.get(url) as response:
                    response.raise_for_status()
                    bodies[url] = await response.text()
    except (aiohttp.ClientError, TimeoutError) as e:
        print(f"No live data: {type(e).__name__}", file=sys.stderr)
        return None
    return bodies


def one_for_each_kind(items: list[dict]) -> list[dict]:
    """Keep the first message of each hazard and level."""
    kept = {}
    for item in sorted(items, key=lambda i: (-i["level"], i["hazard"], i["uf"])):
        kept.setdefault((item["hazard"], item["level"]), item)
    return list(kept.values())


async def messages(host, roots: Path, lang: str, bodies: dict, sample: bool) -> dict:
    """Load the extension in one language and return the text of each poller result."""
    manager_module, registry, present = host

    class Service:
        config = {
            "extensions": {
                "enabled_ids": [ID],
                "settings": json.dumps({ID: {"language": lang}}),
            }
        }

    items = []
    with tempfile.TemporaryDirectory() as data_dir:
        manager = manager_module.ExtensionManager(
            Service(), registry(), roots=[roots], data_dir=Path(data_dir)
        )
        manager.load_all()
        (row,) = manager.status()
        if row["state"] != "loaded":
            raise RuntimeError(row["error"])
        for poller in manager._apis[ID].pollers:
            for envelope in await poller.fetch(ReplaySession(bodies)):
                metadata = envelope.event.metadata
                items.append(
                    {
                        "text": present(envelope, envelope.source_id),
                        "level": metadata["severity_level"],
                        "hazard": metadata["hazard"],
                        "uf": metadata["uf"],
                    }
                )
    registry().unregister_source_entries(owner=ID)
    registry().unregister_presenters(owner=ID)
    return {"total": len(items), "items": one_for_each_kind(items) if sample else items}


def short_commit(directory: Path) -> str:
    """Return the short commit of a directory, or "unknown"."""
    result = subprocess.run(
        ["git", "-C", str(directory), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or "unknown"


async def main(roots: Path, output: Path, offline: bool) -> None:
    """Write the page."""
    host = load_host()
    scenarios = {}
    live = None if offline else await live_bodies(host[0])
    if live:
        scenarios["live"] = {
            lang: await messages(host, roots, lang, live, False) for lang in LANGS
        }
    recorded = recorded_bodies()
    scenarios["recorded"] = {
        lang: await messages(host, roots, lang, recorded, True) for lang in LANGS
    }
    data = {
        "langs": LANGS,
        "captured": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "commit": short_commit(ROOT),
        "host": short_commit(HOST),
        "scenarios": scenarios,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    template = (ROOT / "scripts/mock_template.html").read_text("utf-8")
    output.write_text(template.replace("__DATA__", payload), "utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--offline"]
    asyncio.run(main(Path(args[0]), Path(args[1]), "--offline" in sys.argv))
