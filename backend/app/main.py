from datetime import datetime, timezone
from os import getenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .services.offline_sync import save_synced_packets
from .services.health_engine import build_health_analysis
from .services.mission_timeline import build_mission_timeline
from .services.osdr_research import OSDRUnavailableError, search_osdr_datasets

from .services.telemetry import (
    build_alerts,
    build_baseline_summary,
    generate_telemetry,
)


class TelemetryReading(BaseModel):
    """A synthetic reading queued by the browser during a link outage."""

    timestamp: datetime
    heart_rate_bpm: float = Field(ge=0, le=300)
    spo2_percent: float = Field(ge=0, le=100)
    sleep_hours: float = Field(ge=0, le=24)
    exercise_minutes: int = Field(ge=0, le=1440)


class QueuedTelemetryPacket(BaseModel):
    """One locally queued telemetry sample with a stable deduplication ID."""

    packet_id: str = Field(min_length=1, max_length=100)
    queued_at: datetime
    reading: TelemetryReading


class TelemetrySyncRequest(BaseModel):
    """Batch submitted when a simulated communications link is restored."""

    packets: list[QueuedTelemetryPacket] = Field(min_length=1, max_length=500)


app = FastAPI(
    title="ASTRA Mission Health API",
    description=(
        "A hackathon prototype with synthetic astronaut telemetry and read-only NASA OSDR metadata search. "
        "It is not intended for diagnosis or operational flight decisions."
    ),
    version="0.7.0",
)

# The local web app runs on port 3000 and the API on port 8000. Keep the
# allowed origins explicit instead of opening the API to every website.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        *[
            origin.strip()
            for origin in getenv("ASTRA_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        ],
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def check_api_health() -> dict[str, str]:
    """Confirm that the API process is responding."""
    return {"status": "ok", "service": "astra-api"}


@app.get("/api/v1/mission/overview")
def get_mission_overview() -> dict:
    """Return the summary information used by the dashboard header."""
    readings = generate_telemetry(hours=24, points=25)
    alerts = build_alerts(readings)

    return {
        "mission": {
            "name": "Astra Transit Simulation",
            "mission_day": 214,
            "crew_member": "Crew Member A",
            "mode": "SIMULATION",
            "data_source": "SYNTHETIC",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        "latest": readings[-1],
        "alert_count": len(alerts),
        "status": "ATTENTION" if alerts else "NOMINAL",
    }


@app.get("/api/v1/telemetry")
def get_telemetry(hours: int = Query(default=24, ge=1, le=168)) -> dict:
    """Return sample readings for a period of up to seven days."""
    readings = generate_telemetry(hours=hours, points=max(12, hours + 1))
    return {"source": "synthetic", "hours": hours, "readings": readings}


@app.get("/api/v1/alerts")
def get_health_alerts() -> dict:
    """Return current observations with the evidence behind each one."""
    readings = generate_telemetry(hours=24, points=25)
    return {"source": "synthetic", "alerts": build_alerts(readings)}


@app.get("/api/v1/baseline")
def get_baseline_summary(
    hours: int = Query(default=24, ge=6, le=168),
) -> dict:
    """Compare the two halves of a synthetic telemetry window.

    This endpoint demonstrates explainable trend comparison only. It does not
    establish a real crew member's baseline or provide medical advice.
    """
    readings = generate_telemetry(hours=hours, points=max(12, hours + 1))
    return build_baseline_summary(readings)


@app.get("/api/v1/health-analysis")
def get_health_analysis(
    hours: int = Query(default=24, ge=1, le=168),
) -> dict:
    """Return engineering data-quality checks and descriptive trend comparisons."""
    readings = generate_telemetry(hours=hours, points=max(12, hours + 1))
    return build_health_analysis(readings)


@app.get("/api/v1/mission/timeline")
def get_mission_timeline(
    hours: int = Query(default=24, ge=1, le=168),
) -> dict:
    """Return a chronological view of synthetic telemetry and observations."""
    readings = generate_telemetry(hours=hours, points=max(12, hours + 1))
    return build_mission_timeline(readings, hours)


@app.get("/api/v1/research/osdr")
def search_nasa_osdr(
    term: str = Query(default="human spaceflight", min_length=2, max_length=100),
    limit: int = Query(default=5, ge=1, le=10),
) -> dict:
    """Search NASA OSDR study metadata; this does not ingest study measurements."""
    try:
        return search_osdr_datasets(term, limit)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except OSDRUnavailableError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/v1/telemetry/sync")
def sync_queued_telemetry(request: TelemetrySyncRequest) -> dict:
    """Persist queued demo packets after connectivity returns.

    This local JSONL store is for the hackathon simulation only. It is not a
    production telemetry store and must never receive real medical data.
    """
    try:
        result = save_synced_packets(
            [packet.model_dump(mode="json") for packet in request.packets]
        )
    except OSError as error:
        raise HTTPException(status_code=503, detail="Could not persist queued packets.") from error

    return {
        **result,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "storage": "local-jsonl-demo",
    }
