# Nashhal Newsroom Engine v1

## Pipeline

The newsroom runs as five deterministic stages:

1. **Collector** — discovers events and collects primary/secondary evidence.
2. **Writer** — creates an original Arabic draft from collected material only.
3. **Verifier** — independently checks the event, searches for corroboration, and assigns a verification state.
4. **Editor** — turns verified material into publication-ready Arabic copy without adding unsupported facts.
5. **Publisher** — applies the final invariant gate and writes approved stories to data/news.json.

The existing SEO builder and Nashhal Trust layer then generate article pages, sitemaps, and provenance records.

## Publication policy

Only items that satisfy all conditions are auto-published:

- verification = confirmed
- verification score >= 80
- at least one primary evidence item
- at least one independent evidence item
- editorial status = ready
- title, summary, body, and source URL are present
- the source is fresh enough for the live window

developing and unconfirmed items remain review and are never auto-published.

## Data flow

source discovery -> collected candidate -> written draft -> independent verification -> final edit -> quality gate -> news.json -> article pages -> provenance

## Operational files

- scripts/newsroom/collector.py
- scripts/newsroom/writer.py
- scripts/newsroom/verifier.py
- scripts/newsroom/editor.py
- scripts/newsroom/publisher.py
- scripts/newsroom/orchestrator.py
- scripts/newsroom/self_check.py
- scripts/news_quality_gate.py
- scripts/build_site.py
- scripts/build_provenance.py
- .github/workflows/news-bot.yml

## Secrets and configuration

Required secret:

- XAI_API_KEY

Optional repository variable:

- XAI_MODEL

The code defaults to the repository's existing grok-4.5 setting when XAI_MODEL is not provided.

## Design principle

AI is used as a research and editorial aid. It does not get a free-form publish capability. Publication is a deterministic outcome of source evidence, verification rules, editorial readiness, and the final self-check.


## Degraded mode

If the AI provider returns an authentication, entitlement, rate-limit, or server-availability error, the orchestrator exits safely without creating or publishing new stories. Existing published data is retained and the workflow can continue rebuilding the site.