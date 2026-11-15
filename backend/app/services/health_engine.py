"""Explainable telemetry quality and trend analysis for the ASTRA demo.

All rules in this module are engineering checks for synthetic prototype data.
They are not medical thresholds and must not be used to make health or flight
operations decisions.
"""

from datetime import datetime
from statistics import mean
from typing import Any

from .telemetry import TelemetryReading


REQUIRED_FIELDS = (
    "timestamp",
    "heart_rate_bpm",
    "spo2_percent",
    "sleep_hours",
    "exercise_minutes",
)

# Broad technical sanity bounds used to catch malformed demo packets only.
# These are not healthy/unhealthy ranges or clinical decision thresholds.
NUMERIC_BOUNDS = {
    "heart_rate_bpm": (20, 250),
    "spo2_percent": (50, 100),
    "sleep_hours": (0, 24),
    "exercise_minutes": (0, 1440),
}


def analyze_data_quality(readings: list[TelemetryReading]) -> dict[str, Any]:
    """Score completeness, basic value validity, and timestamp consistency."""
    if not readings:
        return {
            "status": "insufficient_data",
            "score": 0,
            "reading_count": 0,
            "checks": [],
            "summary": "No readings were supplied for quality analysis.",
        }

    missing_fields = 0
    invalid_values = 0
    invalid_timestamps = 0
    parsed_timestamps: list[datetime] = []
    seen_timestamps: set[str] = set()
    duplicate_timestamps = 0

    for reading in readings:
        for field in REQUIRED_FIELDS:
            if field not in reading or reading[field] is None:
                missing_fields += 1

        for field, (minimum, maximum) in NUMERIC_BOUNDS.items():
            value = reading.get(field)
            if not isinstance(value, (int, float)) or not minimum <= value <= maximum:
                invalid_values += 1

        timestamp_text = reading.get("timestamp")
        if not isinstance(timestamp_text, str):
            invalid_timestamps += 1
            continue
        if timestamp_text in seen_timestamps:
            duplicate_timestamps += 1
        seen_timestamps.add(timestamp_text)

        try:
            parsed = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
        except ValueError:
            invalid_timestamps += 1
            continue
        parsed_timestamps.append(parsed)

    required_field_slots = len(readings) * len(REQUIRED_FIELDS)
    numeric_slots = len(readings) * len(NUMERIC_BOUNDS)
    completeness = max(0.0, 1 - missing_fields / required_field_slots)
    value_validity = max(0.0, 1 - invalid_values / numeric_slots)
    timestamp_validity = 1.0
    if invalid_timestamps or duplicate_timestamps:
        timestamp_validity = max(
            0.0,
            1 - (invalid_timestamps + duplicate_timestamps) / len(readings),
        )

    score = round(100 * (0.4 * completeness + 0.4 * value_validity + 0.2 * timestamp_validity))
    if score >= 95:
        status = "good"
        summary = "The supplied demo readings passed the basic integrity checks."
    elif score >= 80:
        status = "review"
        summary = "Some readings need review before trend interpretation."
    else:
        status = "poor"
        summary = "Data integrity issues may make trend interpretation unreliable."

    ordered = parsed_timestamps == sorted(parsed_timestamps)
    checks = [
        {
            "id": "required-fields",
            "label": "Required fields present",
            "status": "pass" if missing_fields == 0 else "review",
            "detail": f"{missing_fields} missing field values across {len(readings)} readings.",
        },
        {
            "id": "numeric-bounds",
            "label": "Technical value bounds",
            "status": "pass" if invalid_values == 0 else "review",
            "detail": f"{invalid_values} numeric values fall outside broad demo sanity bounds.",
        },
        {
            "id": "timestamps",
            "label": "Timestamp integrity",
            "status": "pass" if invalid_timestamps == 0 and duplicate_timestamps == 0 else "review",
            "detail": f"{invalid_timestamps} invalid timestamps and {duplicate_timestamps} duplicate timestamps.",
        },
        {
            "id": "time-order",
            "label": "Chronological ordering",
            "status": "pass" if ordered else "review",
            "detail": "Timestamps are ordered." if ordered else "Readings are not in chronological order.",
        },
    ]

    return {
        "status": status,
        "score": score,
        "reading_count": len(readings),
        "checks": checks,
        "summary": summary,
        "limitations": "Engineering-only checks on synthetic data; not a clinical quality score.",
    }


def _average(readings: list[TelemetryReading], field: str) -> float:
    return mean(float(reading[field]) for reading in readings)


def analyze_trends(readings: list[TelemetryReading]) -> dict[str, Any]:
    """Compare recent and preceding samples and report transparent differences."""
    if len(readings) < 4:
        return {
            "status": "insufficient_data",
            "message": "At least four readings are required for the demo trend comparison.",
            "metrics": [],
        }

    ordered_readings = sorted(readings, key=lambda reading: str(reading.get("timestamp", "")))
    half = max(2, len(ordered_readings) // 2)
    reference = ordered_readings[:half]
    recent = ordered_readings[half:]
    metrics = []

    for field, label, unit in (
        ("heart_rate_bpm", "Heart rate", "bpm"),
        ("spo2_percent", "Blood oxygen", "%"),
        ("sleep_hours", "Sleep duration", "hours"),
        ("exercise_minutes", "Exercise", "minutes"),
    ):
        reference_average = _average(reference, field)
        recent_average = _average(recent, field)
        difference = recent_average - reference_average
        metrics.append({
            "metric": field,
            "label": label,
            "unit": unit,
            "reference_average": round(reference_average, 2),
            "recent_average": round(recent_average, 2),
            "difference": round(difference, 2),
            "reference_samples": len(reference),
            "recent_samples": len(recent),
            "explanation": (
                f"Recent-window mean minus reference-window mean for {label.lower()}. "
                "A change alone does not establish a medical concern."
            ),
        })

    return {
        "status": "available",
        "reference_window": "earlier half of supplied readings",
        "recent_window": "later half of supplied readings",
        "metrics": metrics,
        "limitations": "Trend differences are descriptive only; windows are generated demo data, not a personal baseline.",
    }


def build_health_analysis(readings: list[TelemetryReading]) -> dict[str, Any]:
    """Combine quality checks and descriptive trend comparisons."""
    quality = analyze_data_quality(readings)
    trends = analyze_trends(readings)
    can_interpret_trends = quality["status"] in {"good", "review"} and quality["score"] >= 80

    return {
        "source": "synthetic",
        "quality": quality,
        "trends": trends,
        "interpretation": {
            "status": "available" if can_interpret_trends and trends["status"] == "available" else "limited",
            "message": (
                "Trend summaries are shown with their data-quality context."
                if can_interpret_trends and trends["status"] == "available"
                else "Trend interpretation is limited by data volume or integrity checks."
            ),
        },
        "safety_note": "Prototype only. These outputs are not diagnosis, medical advice, NASA standards, or flight-decision support.",
    }
