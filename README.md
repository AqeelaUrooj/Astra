# ASTRA — Explainable Crew-Health Trends with Offline Telemetry Resilience

ASTRA is a NASA Space Apps Challenge 2026 prototype for inspecting health-related telemetry trends, reviewing a chronological mission event timeline, and demonstrating store-and-forward behavior during a simulated communications outage.

**Important:** the dashboard generates synthetic crew readings. v0.7 adds a live, read-only search of NASA OSDR study metadata for research discovery; it does not download or analyze the study measurements. ASTRA does not use real astronaut telemetry, provide medical diagnosis, or support operational flight decisions. Its rule thresholds and trend calculations are illustrative only.

## Prototype capabilities

- Dark mission-operations dashboard with 6-, 24-, and 72-hour synthetic telemetry views.
- Descriptive comparison between earlier and recent sample windows.
- Engineering data-quality checks and visible evidence for rule-based observations.
- Browser cache for the latest successful dashboard snapshot.
- Simulated communications outage, local packet outbox, and store-and-forward sync.
- FastAPI validation and duplicate packet ID handling in a local JSONL demo store.
- Live NASA OSDR study-metadata search from the dashboard, plus research-context links to the official challenge, NASA HRP, and NASA NLSP.
- Mission event timeline combining synthetic telemetry checkpoints and rule observations with browser-local simulated outage, queue, and sync events.

## Requirements

- Python 3.11+
- Node.js 20.9+
- npm

## Run locally

### 1. Backend

From the extracted `astra-starter` project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

For macOS/Linux, activate the environment with `source .venv/bin/activate`.

- Health endpoint: http://127.0.0.1:8000/health
- Interactive API docs: http://127.0.0.1:8000/docs

### 2. Frontend

Open a second terminal from the project root:

```powershell
cd frontend
npm install
```

Create `frontend/.env.local` with:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Then run:

```powershell
npm run dev
```

Open http://localhost:3000.

## API endpoints

- `GET /health`
- `GET /api/v1/mission/overview`
- `GET /api/v1/telemetry?hours=24`
- `GET /api/v1/alerts`
- `GET /api/v1/baseline?hours=24`
- `GET /api/v1/health-analysis?hours=24`
- `GET /api/v1/mission/timeline?hours=24` — chronological synthetic telemetry checkpoints and explainable observations.
- `POST /api/v1/telemetry/sync`
- `GET /api/v1/research/osdr?term=human%20spaceflight&limit=5` — live NASA OSDR metadata search (requires network access).

## Test

From the project root, with the Python environment active:

```powershell
python -m pytest backend/tests -v
```

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

Only report checks as passing if they were actually run successfully in your environment.

## Demo sequence

1. Load the dashboard while the API is running.
2. In the NASA OSDR panel, search for `human spaceflight` and open a returned study record (requires network access).
3. Click **SIMULATE LINK OUTAGE**.
4. Click **QUEUE DEMO SAMPLE** two or three times.
5. Click **RESTORE LINK & SYNC**.
6. Show the queue count clearing and the synchronization message.
7. Point out the trend evidence, data-quality checks, and explicit synthetic-data labels.

## Submission documentation

- `docs/SUBMISSION_PACK.md` — project description, demo narration, slide outline, and fields to complete.
- `docs/FINAL_CHECKLIST.md` — final test and submission checklist.
- `docs/ARCHITECTURE.md` — architecture and prototype constraints.
- `docs/SOURCES.md` — research context and software source acknowledgements.

## Security and scientific limitations

This is a local hackathon prototype. Browser `localStorage` is not encrypted. The JSONL store has no authentication, authorization, encryption, or production concurrency guarantees. Use synthetic data only. The engineering integrity score is not a medical quality score, and none of the alert thresholds are clinically validated.
