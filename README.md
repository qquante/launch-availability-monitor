# Launch Availability Monitor

> **Local private review:** publication is paused. See [security review and remaining release conditions](docs/SECURITY_REVIEW.md). Local fixes have not been pushed.


A local dashboard that tracks public launch availability transitions, new entries and coverage failures.

![review](https://img.shields.io/badge/review-private-374151) ![primary](https://img.shields.io/badge/primary-Python-2563EB) [![LinkedIn](https://img.shields.io/badge/LinkedIn-Douglas%20Silva-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/douglas-silva-data-analyst/)

[Overview](#overview) · [Architecture](#architecture) · [Setup](#setup) · [Validation](#validation) · [Roadmap](#roadmap) · [Review notes](docs/REVIEW.md)

## Overview

- Strict enabled-state transitions distinguish launch availability from related flags.
- Persistent deduplication survives detector restarts.
- Coverage status and retry/backoff behavior are visible in the local interface.

**Technology:** Python · requests · BeautifulSoup · Playwright · SQLite · HTML dashboard

**Persistence and data:** SQLite persists detector state and deduplicated events. Runtime processes, locks and prior status output are excluded.

## Architecture

```text
Public HTTP/rendered input → detector → persistent transition state → local dashboard and optional audio alert
```

| Location | Review focus |
| --- | --- |
| [`twice_monitor/core.py`](twice_monitor/core.py) | Source/configuration inspected for scope and structure |
| [`twice_monitor/service.py`](twice_monitor/service.py) | Source/configuration inspected for scope and structure |
| [`dashboard.html`](dashboard.html) | Source/configuration inspected for scope and structure |
| [`tests/test_monitor.py`](tests/test_monitor.py) | Source/configuration inspected for scope and structure |

Internal package and module names are retained where changing them would affect imports or compatibility. This descriptive repository name does not imply a completed package/API migration.

## Setup

Install requirements.txt in an isolated Python environment. Run python -m unittest discover -s tests -v before installing browser runtimes or starting the monitor.

Start from an isolated environment. Use `.env.example` when present and inspect the configuration loader: an example file is not necessarily loaded automatically. Runtime databases, real account sessions and private credentials are not bundled. Live integration prerequisites are separate from local tests.

## Validation

Static parsing checked 5 Python files and 4 strict JSON files. Python syntax errors: 0; JSON errors: 0. The selected offline suite passed.

```console
python -m unittest discover -s tests -v
```

These results apply to the selected checks on the preparation copy. They do not establish deployment readiness, full coverage, live provider availability or measured performance. CI definitions, when present under `docs/ci-templates/`, are inactive review templates; no remote CI badge is claimed.

## Limits and current status

Offline tests do not prove current website selectors or one-second detection reliability. No browser or monitoring loop was started. Endpoint changes and throttling can reduce coverage.

This private snapshot is for code and portfolio review. Generated runtime material and unreviewed binary assets may be excluded. [Review notes](docs/REVIEW.md) record preparation scope, findings and outstanding validation.

## Roadmap

- [ ] Keep HTTP and rendered-page fixtures versioned.
- [ ] Validate selectors in a short, read-only session.
- [ ] Document failure visibility and source-specific backoff.

## History and attribution

No recoverable original Git history was verified for this snapshot. Import and preparation commits use their actual current dates; filesystem timestamps are not treated as development dates.

No open-source license is granted by this preparation. A license and attribution review is required before public redistribution.

## Maintainer and feedback

Douglas de Oliveira Silva · [GitHub](https://github.com/qquante) · [LinkedIn](https://www.linkedin.com/in/douglas-silva-data-analyst/)

For this private review, report reproducible issues with a minimal fixture and the exact check output. Keep account data, credentials and generated sensitive reports out of issues and commits. Existing contribution guidelines apply where present.

**Topics:** `python`, `playwright`, `sqlite`, `monitoring`, `web-automation`, `dashboard`
