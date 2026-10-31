"""Build the source entries and the event envelopes of the host."""

from __future__ import annotations

ID = "br_south_disaster"
ALERTS_SOURCE = f"{ID}_cemaden_alerts"
RAIN_SOURCE = f"{ID}_cemaden_rain"
PRESENTER_KEY = f"{ID}_weather"


def _envelope(api, event_id, metadata, when, raw):
    m = api.models
    hazard = metadata["hazard"]
    source_id = RAIN_SOURCE if hazard == "rain" else ALERTS_SOURCE
    headline = api.t(
        "headline.rain" if hazard == "rain" else "headline.alert",
        level=api.t(f"level.{metadata['severity_level']}"),
        municipio=metadata["municipio"],
        uf=metadata["uf"],
    )
    identity = m.EventIdentity(
        event_id=event_id,
        source_id=source_id,
        event_type="weather_alarm",
        provider_family="extension",
        source_enum=source_id,
        published_at=when,
    )
    event = m.WeatherEvent(
        title=api.t(f"title.{hazard}"),
        headline=headline,
        effective_at=when,
        metadata=metadata,
    )
    payload = m.SourcePayload(source_id=source_id, provider_family="extension", raw=raw)
    return m.EventEnvelope(identity=identity, event=event, payload=payload)


def build_alert_envelope(api, alert: dict, enso: dict | None):
    """Build the event envelope for a CEMADEN alert.

    The event time is the last update time.
    """
    raw = alert["raw"]
    issued = alert["issued_at"]
    metadata = {
        "severity_level": alert["level"],
        "uf": raw.get("uf"),
        "codibge": raw.get("codibge"),
        "municipio": raw.get("municipio"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "hazard": alert["hazard"],
        "issue_time": issued.isoformat() if issued else None,
        "enso": enso,
    }
    event_id = f"{ID}_cemaden_{alert['cod_alerta']}"
    return _envelope(api, event_id, metadata, alert["updated_at"] or issued, raw)


def build_rain_envelope(api, item: dict, day: str, enso: dict | None):
    """Build the event envelope for a rain gauge item.

    The event time is the time of the gauge reading.
    """
    observed = item["observed_at"]
    metadata = {
        "severity_level": item["level"],
        "uf": item["uf"],
        "codibge": item["codibge"],
        "municipio": item["municipio"],
        "hazard": "rain",
        "station": item["station"],
        "acc1hr": item["acc1hr"],
        "acc24hr": item["acc24hr"],
        "issue_time": observed.isoformat() if observed else None,
        "enso": enso,
    }
    event_id = f"{ID}_rain_{item['codibge']}_{day}_{item['level']}"
    raw = {k: v for k, v in item.items() if k not in ("rank", "observed_at")}
    return _envelope(api, event_id, metadata, observed, raw)


def source_entry(api, source_id: str, kind: str, priority: int):
    m = api.models
    return m.SourceEntry(
        source_id=source_id,
        source_enum=source_id,
        source_type=m.SourceType.WEATHER,
        provider_family=m.ProviderFamily.EXTENSION,
        config_group="extensions",
        config_key=source_id,
        parser_name="",
        presentation_type="weather",
        text_presenter_key=PRESENTER_KEY,
        report_policy="none",
        intensity_mode="none",
        priority=priority,
        display_name=api.t(f"source.{kind}"),
        description=api.t(f"source.{kind}.desc"),
        default_timezone="America/Sao_Paulo",
        fingerprint_prefix=source_id,
        dispatch_family=source_id,
        provider_aliases=(source_id,),
        routing_tags=("extension", "brazil", "south", "http"),
    )
