from datetime import datetime, timedelta, timezone
import math
from typing import Any


TelemetryReading = dict[str, Any]
HealthAlert = dict[str, str]


def generate_telemetry(hours: int = 24, points: int = 25) -> list[TelemetryReading]:
    """Create predictable sample readings for the dashboard demo.

    These values are synthetic. They let us test the interface and alert rules
    before connecting a real, appropriately sourced research dataset.
    """
    if hours < 1:
        raise ValueError("hours must be at least 1")
    if points < 2:
        raise ValueError("points must be at least 2")

    now = datetime.now(timezone.utc)
    readings: list[TelemetryReading] = []

    for index in range(points):
        progress = index / (points - 1)
        timestamp = now - timedelta(hours=hours * (1 - progress))

        # Add a gradual change later in the timeline so the demo can show
        # how a trend-based rule works.
        trend_has_started = progress > 0.72
        heart_rate = 62 + 2.2 * math.sin(index / 2.8)
        if trend_has_started:
            heart_rate += 8

        sleep_hours = 7.4 - 1.7 * max(0, (progress - 0.55) / 0.45)
        exercise_minutes = 45 if progress < 0.72 else 28
        oxygen_saturation = 98 + 0.4 * math.sin(index / 3.2)

        readings.append({
            "timestamp": timestamp.isoformat(),
            "heart_rate_bpm": round(heart_rate, 1),
            "spo2_percent": round(oxygen_saturation, 1),
            "sleep_hours": round(sleep_hours, 1),
            "exercise_minutes": exercise_minutes,
        })

    return readings


def build_alerts(readings: list[TelemetryReading]) -> list[HealthAlert]:
    """Return explainable observations using illustrative prototype rules.

    These comparisons have not been clinically validated and must not be
    used for medical diagnosis or operational flight decisions.
    """
    if not readings:
        return []

    recent_readings = readings[-6:]
    earlier_readings = readings[:max(1, len(readings) // 2)]

    earlier_heart_rate = sum(
        reading["heart_rate_bpm"] for reading in earlier_readings
    ) / len(earlier_readings)
    recent_heart_rate = sum(
        reading["heart_rate_bpm"] for reading in recent_readings
    ) / len(recent_readings)
    recent_sleep = sum(
        reading["sleep_hours"] for reading in recent_readings
    ) / len(recent_readings)
    recent_exercise = sum(
        reading["exercise_minutes"] for reading in recent_readings
    ) / len(recent_readings)

    alerts: list[HealthAlert] = []

    if recent_heart_rate - earlier_heart_rate >= 5:
        alerts.append({
            "id": "trend-heart-rate",
            "severity": "watch",
            "title": "Heart-rate trend above demo baseline",
            "evidence": (
                f"Recent average: {recent_heart_rate:.1f} bpm. "
                f"Earlier-window average: {earlier_heart_rate:.1f} bpm."
            ),
            "recommended_action": (
                "Check sensor quality, review reported symptoms, and follow "
                "the mission's approved crew-health protocol."
            ),
            "rule_id": "HR_TREND_01",
        })

    if recent_sleep < 6.5:
        alerts.append({
            "id": "trend-sleep",
            "severity": "watch",
            "title": "Sleep duration trend reduced",
            "evidence": (
                f"Recent average sleep is {recent_sleep:.1f} hours per "
                "24-hour period in this simulation."
            ),
            "recommended_action": (
                "Complete the daily well-being check-in and review schedule, "
                "workload, and sleep conditions."
            ),
            "rule_id": "SLEEP_TREND_01",
        })

    if recent_exercise < 30:
        alerts.append({
            "id": "trend-exercise",
            "severity": "info",
            "title": "Exercise completion below demo target",
            "evidence": (
                f"Recent average exercise is {recent_exercise:.0f} minutes "
                "per day in this simulation."
            ),
            "recommended_action": (
                "Review the activity log and follow the mission's established "
                "exercise plan."
            ),
            "rule_id": "EXERCISE_TREND_01",
        })

    return alerts


def build_baseline_summary(readings: list[TelemetryReading]) -> dict[str, Any]:
    """Compare recent simulated readings with an earlier window.

    The reference window is generated for demonstration purposes; it is not a
    medically meaningful personal baseline and should never drive real care.
    """
    if len(readings) < 4:
        return {
            "source": "synthetic",
            "status": "insufficient_data",
            "message": "At least four readings are needed for this demo comparison.",
        }

    split_index = max(2, len(readings) // 2)
    reference_window = readings[:split_index]
    recent_window = readings[split_index:]

    def average(field: str, window: list[TelemetryReading]) -> float:
        return sum(float(reading[field]) for reading in window) / len(window)

    reference_heart_rate = average("heart_rate_bpm", reference_window)
    recent_heart_rate = average("heart_rate_bpm", recent_window)
    difference = recent_heart_rate - reference_heart_rate

    if difference >= 5:
        trend_status = "increased"
    elif difference <= -5:
        trend_status = "decreased"
    else:
        trend_status = "similar"

    return {
        "source": "synthetic",
        "status": "available",
        "metric": "heart_rate_bpm",
        "reference_average": round(reference_heart_rate, 1),
        "recent_average": round(recent_heart_rate, 1),
        "difference": round(difference, 1),
        "trend_status": trend_status,
        "reference_readings": len(reference_window),
        "recent_readings": len(recent_window),
        "explanation": (
            "Compares the first and second portions of this generated time "
            "series. This is an illustrative demo baseline, not a validated "
            "personal or clinical reference."
        ),
    }
