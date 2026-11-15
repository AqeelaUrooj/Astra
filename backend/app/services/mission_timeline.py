"""Build a chronological, explainable timeline for the ASTRA demo."""

from datetime import datetime
from typing import Any

from backend.app.services.telemetry import build_alerts

TelemetryReading = dict[str, Any]
TimelineEvent = dict[str, Any]


def build_mission_timeline(
    readings: list[TelemetryReading],
    hours: int,
) -> dict[str, Any]:
    """Summarize synthetic telemetry checkpoints and rule observations.

    Events are descriptive records generated from the same synthetic readings
    as the dashboard. This is not a log of real mission activity or astronaut
    health events.
    """
    if not readings:
        return {
            "source": "synthetic",
            "hours": hours,
            "events": [],
            "limitations": "No readings are available for this timeline window.",
        }

    events: list[TimelineEvent] = []
    checkpoint_count = min(8, len(readings))
    checkpoint_indexes = {
        round(index * (len(readings) - 1) / max(1, checkpoint_count - 1))
        for index in range(checkpoint_count)
    }

    for index in sorted(checkpoint_indexes):
        reading = readings[index]
        events.append({
            "id": f"telemetry-{index}",
            "timestamp": reading["timestamp"],
            "category": "telemetry",
            "severity": "info",
            "title": "Telemetry checkpoint recorded",
            "description": (
                f"Heart rate {float(reading['heart_rate_bpm']):.1f} bpm · "
                f"SpO₂ {float(reading['spo2_percent']):.1f}% · "
                f"Sleep {float(reading['sleep_hours']):.1f} h"
            ),
            "source": "Synthetic telemetry generator",
        })

    for alert in build_alerts(readings):
        events.append({
            "id": f"alert-{alert['id']}",
            "timestamp": readings[-1]["timestamp"],
            "category": "alert",
            "severity": alert["severity"],
            "title": alert["title"],
            "description": alert["evidence"],
            "source": alert["rule_id"],
        })

    events.sort(key=lambda event: _parse_timestamp(event["timestamp"]))
    return {
        "source": "synthetic",
        "hours": hours,
        "events": events,
        "limitations": (
            "Timeline entries are generated from synthetic demo telemetry and "
            "illustrative rules; they are not records of real mission events."
        ),
    }


def _parse_timestamp(value: str) -> datetime:
    """Parse ISO timestamps consistently for chronological sorting."""
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return parsed
