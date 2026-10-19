# Launch Availability Monitor

A local dashboard that tracks public launch availability transitions, new entries and coverage failures.

## Features

- Strict enabled-state transitions distinguish launch availability from related flags.
- Persistent deduplication survives detector restarts.
- Coverage status and retry/backoff behavior are visible in the local interface.

## Stack

Python · requests · BeautifulSoup · Playwright · SQLite · HTML dashboard

SQLite persists detector state and deduplicated events. Runtime processes, locks and prior status output are excluded.

## Getting started

Install requirements.txt in an isolated Python environment. Run python -m unittest discover -s tests -v before installing browser runtimes or starting the monitor.

## How it works

```text
Public HTTP/rendered input → detector → persistent transition state → local dashboard and optional audio alert
```

## Current limitations

Offline tests do not prove current website selectors or one-second detection reliability. No browser or monitoring loop was started. Endpoint changes and throttling can reduce coverage.

## Tests

```console
python -m unittest discover -s tests -v
```

These checks use offline fixtures or controlled backends.

## License

No open-source license has been granted. Redistribution terms remain to be defined.
