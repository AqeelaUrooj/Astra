# ASTRA final submission checklist

## Build and demo

- [ ] Backend starts using the documented command.
- [ ] Frontend starts using the documented command.
- [ ] `GET /health` returns `{"status":"ok","service":"astra-api"}`.
- [ ] Dashboard loads overview, telemetry, observations, baseline, and analysis without console errors.
- [ ] 6h, 24h, and 72h time windows work.
- [ ] Data-quality checks and trend comparison render.
- [ ] Outage demo: pause link, queue 2–3 packets, restore link, verify queued count clears.
- [ ] Retry one packet ID and verify the API reports it as a duplicate rather than storing it twice.
- [ ] Run backend tests: `python -m pytest backend/tests -v`.
- [ ] Run frontend lint/build if dependencies install cleanly: `cd frontend`, `npm run lint`, `npm run build`.
- [ ] If frontend build cannot be run, do not claim it passed; record the limitation.

## Submission assets

- [ ] Public repository URL opens in a private/incognito browser window.
- [ ] Demo URL opens without requesting private access, or the submission clearly provides a recorded demo.
- [ ] Demo is concise and demonstrates the actual implemented features.
- [ ] Project title, challenge, team roster, and description are accurate.
- [ ] `docs/SUBMISSION_PACK.md` fields have been completed and reviewed.
- [ ] NASA sources and software/asset sources are cited.
- [ ] AI-use disclosure accurately lists tools used and their role.
- [ ] Synthetic data and non-clinical limitations are visible in the UI and submission.
- [ ] Verify the deadline and eligibility requirements with the specific registered local event.
- [ ] Click Submit and verify the project status/confirmation; save proof.

## Do not claim unless verified

- NASA study measurement analysis or real astronaut data; v0.6 introduced NASA OSDR metadata search, while v0.7 adds a synthetic/local mission event timeline.
- Medical validation, diagnostic accuracy, NASA endorsement, or flight readiness.
- A passing frontend build when `npm run build` was not run successfully.
- Deployment uptime or public availability without opening the deployed link yourself.

- [ ] Search NASA OSDR from the Research Context panel; confirm results include source links or document if the external service is unavailable.
