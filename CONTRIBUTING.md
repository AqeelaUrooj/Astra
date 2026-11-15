# ASTRA contribution guide

We want code that teammates can read, explain, and safely extend.

## Everyday guidelines
- Use descriptive names. Prefer `recent_readings` over `r`.
- Keep functions focused on one job.
- Add Python type hints and TypeScript types for API data.
- Explain domain assumptions and non-obvious trade-offs in comments.
- Handle missing data and network errors deliberately.
- Never describe synthetic values as real NASA telemetry.
- Treat alert thresholds as prototypes until they have a defensible scientific basis and review.
- Never commit API keys, tokens, `.env.local`, or personal health data.

## Pull requests
1. Explain what changed and why.
2. Include steps to test the change.
3. Add tests for new rules and API behavior.
4. Ask a teammate to review before merging into `main`.
