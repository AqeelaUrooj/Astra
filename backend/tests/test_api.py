from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.telemetry import build_alerts, generate_telemetry


client = TestClient(app)


def test_health_endpoint_reports_api_status():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "astra-api"}


def test_telemetry_endpoint_returns_synthetic_readings():
    response = client.get("/api/v1/telemetry?hours=24")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "synthetic"
    assert len(body["readings"]) >= 12
    assert "heart_rate_bpm" in body["readings"][0]
    assert "timestamp" in body["readings"][0]


def test_telemetry_endpoint_rejects_invalid_period():
    response = client.get("/api/v1/telemetry?hours=999")
    assert response.status_code == 422


def test_alerts_include_evidence_and_next_step():
    response = client.get("/api/v1/alerts")

    assert response.status_code == 200
    for alert in response.json()["alerts"]:
        assert alert["evidence"]
        assert alert["recommended_action"]
        assert alert["rule_id"]


def test_empty_telemetry_does_not_create_alerts():
    assert build_alerts([]) == []


def test_generator_rejects_too_few_points():
    try:
        generate_telemetry(points=1)
    except ValueError as error:
        assert "points" in str(error)
    else:
        raise AssertionError("Expected generator to reject one point")


def test_baseline_endpoint_explains_its_synthetic_reference():
    response = client.get("/api/v1/baseline?hours=24")

    assert response.status_code == 200
    result = response.json()
    assert result["source"] == "synthetic"
    assert result["status"] == "available"
    assert "reference_average" in result
    assert "recent_average" in result
    assert "not a validated" in result["explanation"]


def test_baseline_endpoint_rejects_too_short_window():
    response = client.get("/api/v1/baseline?hours=2")

    assert response.status_code == 422


def test_offline_sync_persists_packets_and_deduplicates_retries(tmp_path, monkeypatch):
    from backend.app.services import offline_sync

    monkeypatch.setattr(offline_sync, "STORE_PATH", tmp_path / "synced_packets.jsonl")
    packet = {
        "packet_id": "packet-test-001",
        "queued_at": "2026-11-15T10:00:00Z",
        "reading": {
            "timestamp": "2026-11-15T09:59:00Z",
            "heart_rate_bpm": 72.0,
            "spo2_percent": 98.0,
            "sleep_hours": 7.5,
            "exercise_minutes": 30,
        },
    }

    first = offline_sync.save_synced_packets([packet])
    second = offline_sync.save_synced_packets([packet])

    assert first == {"received_count": 1, "stored_count": 1, "duplicate_count": 0}
    assert second == {"received_count": 1, "stored_count": 0, "duplicate_count": 1}
    assert len((tmp_path / "synced_packets.jsonl").read_text().splitlines()) == 1


def test_sync_endpoint_rejects_out_of_range_reading():
    response = client.post("/api/v1/telemetry/sync", json={"packets": [{
        "packet_id": "bad-packet",
        "queued_at": "2026-11-15T10:00:00Z",
        "reading": {
            "timestamp": "2026-11-15T09:59:00Z",
            "heart_rate_bpm": 72,
            "spo2_percent": 101,
            "sleep_hours": 7,
            "exercise_minutes": 20,
        },
    }]})

    assert response.status_code == 422


def test_sync_endpoint_stores_valid_packet(tmp_path, monkeypatch):
    from backend.app.services import offline_sync

    monkeypatch.setattr(offline_sync, "STORE_PATH", tmp_path / "api_synced_packets.jsonl")
    response = client.post("/api/v1/telemetry/sync", json={"packets": [{
        "packet_id": "api-packet-001",
        "queued_at": "2026-11-15T10:00:00Z",
        "reading": {
            "timestamp": "2026-11-15T09:59:00Z",
            "heart_rate_bpm": 72,
            "spo2_percent": 98,
            "sleep_hours": 7,
            "exercise_minutes": 20,
        },
    }]})

    assert response.status_code == 200
    assert response.json()["stored_count"] == 1
    assert response.json()["storage"] == "local-jsonl-demo"
    assert (tmp_path / "api_synced_packets.jsonl").exists()


def test_health_analysis_endpoint_returns_quality_checks_and_trends():
    response = client.get("/api/v1/health-analysis?hours=24")

    assert response.status_code == 200
    result = response.json()
    assert result["source"] == "synthetic"
    assert result["quality"]["score"] >= 0
    assert result["quality"]["score"] <= 100
    assert {check["id"] for check in result["quality"]["checks"]} == {
        "required-fields", "numeric-bounds", "timestamps", "time-order"
    }
    assert len(result["trends"]["metrics"]) == 4
    assert "not diagnosis" in result["safety_note"]


def test_health_analysis_rejects_invalid_window():
    response = client.get("/api/v1/health-analysis?hours=999")
    assert response.status_code == 422


def test_data_quality_flags_out_of_bounds_values():
    from backend.app.services.health_engine import analyze_data_quality

    reading = {
        "timestamp": "2026-11-15T10:00:00+00:00",
        "heart_rate_bpm": 999,
        "spo2_percent": 98,
        "sleep_hours": 7,
        "exercise_minutes": 30,
    }
    report = analyze_data_quality([reading])

    assert report["status"] == "review"
    numeric_check = next(check for check in report["checks"] if check["id"] == "numeric-bounds")
    assert numeric_check["status"] == "review"


def test_data_quality_handles_empty_input():
    from backend.app.services.health_engine import analyze_data_quality

    report = analyze_data_quality([])
    assert report["status"] == "insufficient_data"
    assert report["score"] == 0


def test_osdr_research_endpoint_returns_provenance_and_results(monkeypatch):
    from backend.app import main

    expected = {
        "source": "NASA Open Science Data Repository",
        "source_url": "https://osdr.nasa.gov/osdr/data/search",
        "search_term": "sleep in space",
        "result_count": 1,
        "results": [{
            "title": "Sleep in space research study",
            "accession": "OSD-123",
            "description": "Study metadata summary",
            "release_date": "2024-01-01",
            "organism": "Homo sapiens",
            "url": "https://osdr.nasa.gov/bio/repo/data/studies/OSD-123",
        }],
        "provenance_note": "Metadata only; not clinical evidence.",
    }
    monkeypatch.setattr(main, "search_osdr_datasets", lambda term, limit: expected)

    response = client.get("/api/v1/research/osdr?term=sleep%20in%20space")

    assert response.status_code == 200
    assert response.json() == expected


def test_osdr_research_endpoint_rejects_short_search_term():
    response = client.get("/api/v1/research/osdr?term=x")

    assert response.status_code == 422


def test_osdr_research_endpoint_reports_upstream_unavailable(monkeypatch):
    from backend.app import main
    from backend.app.services.osdr_research import OSDRUnavailableError

    def fail_search(term, limit):
        raise OSDRUnavailableError("NASA OSDR search is temporarily unavailable.")

    monkeypatch.setattr(main, "search_osdr_datasets", fail_search)
    response = client.get("/api/v1/research/osdr?term=human%20spaceflight")

    assert response.status_code == 502
    assert response.json()["detail"] == "NASA OSDR search is temporarily unavailable."


def test_osdr_parser_normalizes_search_index_records():
    from backend.app.services.osdr_research import _extract_records, _normalize_record

    payload = {
        "hits": {
            "hits": [{
                "_source": {
                    "Study Title": ["Spaceflight Sleep Study"],
                    "Accession": ["OSD-321"],
                    "Study Description": ["A short metadata summary"],
                    "Organism": ["Homo sapiens"],
                }
            }]
        }
    }

    records = _extract_records(payload)
    result = _normalize_record(records[0], "sleep")

    assert result["title"] == "Spaceflight Sleep Study"
    assert result["accession"] == "OSD-321"
    assert result["organism"] == "Homo sapiens"
    assert result["url"].endswith("/OSD-321")


def test_mission_timeline_returns_sorted_synthetic_events():
    response = client.get("/api/v1/mission/timeline?hours=24")

    assert response.status_code == 200
    result = response.json()
    assert result["source"] == "synthetic"
    assert result["hours"] == 24
    assert result["events"]
    timestamps = [event["timestamp"] for event in result["events"]]
    assert timestamps == sorted(timestamps)
    assert any(event["category"] == "telemetry" for event in result["events"])
    assert "synthetic demo telemetry" in result["limitations"]


def test_mission_timeline_rejects_invalid_window():
    response = client.get("/api/v1/mission/timeline?hours=999")
    assert response.status_code == 422


def test_mission_timeline_includes_alert_evidence_when_rules_trigger():
    from backend.app.services.mission_timeline import build_mission_timeline

    readings = [
        {
            "timestamp": f"2026-11-15T{hour:02d}:00:00+00:00",
            "heart_rate_bpm": 60 if hour < 6 else 72,
            "spo2_percent": 98,
            "sleep_hours": 7.5,
            "exercise_minutes": 35,
        }
        for hour in range(12)
    ]
    result = build_mission_timeline(readings, 12)
    alert_events = [event for event in result["events"] if event["category"] == "alert"]
    assert alert_events
    assert all(event["description"] for event in alert_events)
    assert all(event["source"] for event in alert_events)
