---
name: gilberto-process-ingest
description: Classify files dropped in `_ingest/` into a pillar (me, pulse, projects, intelligence, journey) and dispatch to `gilberto-capability-<pillar>-archive`. Triggered by the ingest launchd job (WatchPaths) or manually. Use to file new drops.
---

# gilberto-process-ingest

CAPTURE step. You classify; `script.py` does every filesystem action (lock, stability, dispatch, collision suffix, sidecars). Never move, write or delete in the vault yourself. Paths confined to `$GILBERTO_ROOT/_ingest/`.

## First run: activation

```bash
python3 "$(dirname "$0")/activate.py"
```

Idempotent. Loads the `com.foomakers.gilberto.ingest` job via `launchctl bootstrap` when this skill is installed and the plist exists (written by `gilberto install`); otherwise exit 0, nothing loaded. Output: JSON `status` = `loaded` | `already-loaded` | `skipped` (+ `reason`).

## Run

1. `python3 script.py scan [--min-age=5]` → `{status, files}`. `status: skipped` (`locked`) ⇒ another run is active: stop. Files modified < `--min-age` s (still copying) and files with an `.error.md` are not listed; a later WatchPaths event retries.
2. For each file: read it, choose `pillar` ∈ {me, pulse, projects, intelligence, journey} and `confidence` ∈ [0,1]. No fit ⇒ `--pillar=none`.
3. `python3 script.py apply --file=<name> --pillar=<p> --confidence=<c> [--threshold=0.7]`

`apply` outcomes (JSON, exit 0): `archived` (+ `archived` path) · `kept` (confidence < threshold; file stays, proposal sidecar owned by #74) · `skipped` (`locked` | `unstable`) · `error` (`UNSUPPORTED` | `UNCLASSIFIABLE` | `ARCHIVE_MISSING` | `ARCHIVE_FAILED`; file stays, `<name>.error.md` written). Exit 1: `INVALID_PATH`, `NOT_FOUND`.

## Archive contract

Capability `gilberto-capability-<pillar>-archive` (found like `dispatch.sh`, dir under `*/skills/`) is run as `python3 script.py --source=<abs path> --pillar=<p> --name=<final name>`; it must create `$GILBERTO_ROOT/<pillar>/<name>` and exit 0. `<name>` is collision-free (`a.pdf` → `a-1.pdf`), never overwrites. On success ingest writes `<pillar>/<name>.ingest.json` (`source`, `pillar`, `confidence`, `ingested_at`) and removes the source from `_ingest/`.

Supported: pdf md txt html docx png jpg jpeg. One run at a time (`_ingest/.ingest.lock`, non-blocking).
