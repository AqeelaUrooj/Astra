# ASTRA sources and acknowledgements

Accessed/reviewed for project context on 15 November 2026. Recheck links and access terms before submission.

## Challenge and research context

1. **NASA Space Apps Challenge 2026 — Create Health Monitoring Software for Astronauts on Space Missions.** Challenge statement and resources. https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/?tab=resources
2. **NASA Open Science Data Repository (OSDR).** Repository for space life-sciences research datasets. https://osdr.nasa.gov/
   - API documentation: https://www.nasa.gov/osdr-api/
   - ASTRA integration: backend `GET /api/v1/research/osdr?term=human%20spaceflight` searches public study metadata. Accessed metadata should be checked against each study record before reuse.
3. **NASA Human Research Program (HRP).** Background on risks and research priorities related to human spaceflight. https://www.nasa.gov/hrp/
4. **NASA Life Sciences Portal (NLSP).** Discovery of NASA life-sciences studies and resources. https://nlsp.nasa.gov/
5. **NASA Space Apps 2026 project submission guidance.** https://www.spaceappschallenge.org/resources/project-submission-guide

**Important provenance note:** items 1–4 are references for challenge/scientific context. ASTRA v0.6 introduced a live, read-only search of NASA OSDR study metadata via the OSDR public search API. It does not download or analyze study measurement files and does not use OSDR records as live crew telemetry or medical thresholds. Do not list them as datasets used by the running application.

The v0.7 mission event timeline combines synthetic telemetry checkpoints and rule observations with browser-local simulated outage and sync actions. These are demo events, not NASA mission records.

## Software and libraries

The project uses the following libraries; check their current license files and include any additional packages/assets introduced by your team.

- Next.js: https://nextjs.org/
- React: https://react.dev/
- Recharts: https://recharts.org/
- Lucide React: https://lucide.dev/
- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/
- pytest: https://docs.pytest.org/

## Third-party assets

The current UI is built from code and icon components. If your team adds external photographs, illustrations, fonts, sound, video, or other assets, add the original source, creator, license, and attribution requirements here before submitting.


## Timeline provenance note (v0.7)

The mission timeline is generated from ASTRA's synthetic telemetry and illustrative rules. Communications and synchronization events are recorded in the user's browser local storage for demonstration purposes. These entries are not NASA mission records and should not be described as real astronaut activity.
