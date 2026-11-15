"""Small, read-only integration with NASA's Open Science Data Repository.

This module searches study metadata only. It does not download raw data, map
research measurements to crew telemetry, or use research records as medical
thresholds. That separation is intentional for the ASTRA prototype.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

OSDR_SEARCH_URL = "https://osdr.nasa.gov/osdr/data/search"
OSDR_PORTAL_SEARCH_URL = "https://osdr.nasa.gov/bio/repo/search"
REQUEST_TIMEOUT_SECONDS = 8.0


class OSDRUnavailableError(RuntimeError):
    """Raised when NASA OSDR cannot be reached or returns an invalid response."""


def _first_value(record: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value among known OSDR field-name variants."""
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _text(value: Any) -> str | None:
    """Normalize scalar or list-shaped metadata to a safe display string."""
    if value is None or isinstance(value, dict):
        return None
    if isinstance(value, list):
        value = next((item for item in value if item not in (None, "")), None)
    if value is None or isinstance(value, (dict, list)):
        return None
    result = str(value).strip()
    return result[:600] if result else None


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    """Handle the common list and search-index shapes used by metadata APIs."""
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        hits = payload.get("hits")
        if isinstance(hits, dict) and isinstance(hits.get("hits"), list):
            candidates = hits["hits"]
        elif isinstance(hits, list):
            candidates = hits
        else:
            candidates = next(
                (
                    payload[key]
                    for key in ("results", "studies", "data", "items")
                    if isinstance(payload.get(key), list)
                ),
                [],
            )
    else:
        candidates = []

    records: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        nested = candidate.get("_source") or candidate.get("source") or candidate.get("metadata")
        records.append(nested if isinstance(nested, dict) else candidate)
    return records


def _normalize_record(record: dict[str, Any], search_term: str) -> dict[str, str | None]:
    """Map a NASA study record into a stable, UI-friendly representation."""
    title = _text(_first_value(record, "Study Title", "study_title", "title", "Title"))
    accession = _text(
        _first_value(record, "Accession", "Study Accession", "accession", "study_accession", "id")
    )
    description = _text(
        _first_value(
            record,
            "Study Description",
            "Study Abstract",
            "description",
            "abstract",
            "Summary",
        )
    )
    release_date = _text(
        _first_value(record, "Study Public Release Date", "release_date", "Release Date", "date")
    )
    organism = _text(_first_value(record, "organism", "Organism", "Study Organism"))

    study_id = accession or ""
    if study_id and not study_id.upper().startswith("OSD-"):
        if study_id.isdigit():
            study_id = f"OSD-{study_id}"
    study_url = (
        f"https://osdr.nasa.gov/bio/repo/data/studies/{quote(study_id, safe='-')}"
        if study_id.startswith("OSD-")
        else f"{OSDR_PORTAL_SEARCH_URL}?q={quote(search_term)}&data_source=cgene"
    )

    return {
        "title": title or "Untitled NASA OSDR study",
        "accession": study_id or None,
        "description": description,
        "release_date": release_date,
        "organism": organism,
        "url": study_url,
    }


def search_osdr_datasets(search_term: str, limit: int = 5) -> dict[str, Any]:
    """Search NASA OSDR metadata and return a small, normalized result set."""
    term = " ".join(search_term.split()).strip()
    if len(term) < 2:
        raise ValueError("Search term must contain at least two characters.")

    try:
        response = httpx.get(
            OSDR_SEARCH_URL,
            params={"term": term, "from": 0, "size": limit, "type": "cgene"},
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"Accept": "application/json", "User-Agent": "ASTRA-hackathon-prototype/0.6"},
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise OSDRUnavailableError("NASA OSDR search is temporarily unavailable.") from error

    records = _extract_records(payload)
    normalized = [_normalize_record(record, term) for record in records[:limit]]
    return {
        "source": "NASA Open Science Data Repository",
        "source_url": OSDR_SEARCH_URL,
        "search_term": term,
        "result_count": len(normalized),
        "results": normalized,
        "provenance_note": (
            "These are NASA OSDR study-metadata search results. ASTRA does not use these records "
            "as crew telemetry, medical thresholds, or validated clinical evidence. Review each "
            "study's methods, population, access terms, and limitations before reuse."
        ),
    }
