---
name: gilberto-process-ingest
description: Classify files dropped in `_ingest/` into a pillar (me, pulse, projects, intelligence, journey) and dispatch to `gilberto-capability-<pillar>-archive`. Triggered by the ingest launchd job (WatchPaths) or manually. Use to file new drops.
---

# gilberto-process-ingest

CAPTURE step. You classify; `script.py` does every filesystem action (lock, stability, dispatch, collision suffix, sidecars). Never move, write or delete in the vault yourself. Paths confined to `$GILBERTO_ROOT/_ingest/` (top level and `_ingest/intelligence/`, listed/accepted as `intelligence/<file>`; archived under `<pillar>/<basename>`).

## First run: activation

```bash
python3 "$(dirname "$0")/activate.py"
```

Idempotent. Loads the `com.foomakers.gilberto.ingest` job via `launchctl bootstrap` when this skill is installed and the plist exists (written by `gilberto install`); otherwise exit 0, nothing loaded. Output: JSON `status` = `loaded` | `already-loaded` | `skipped` (+ `reason`).

## Run

1. `python3 script.py scan [--min-age=5]` → `{status, files}`. `status: skipped` (`locked`) ⇒ another run is active: stop. Files modified < `--min-age` s (still copying) and files with an `.error.md` or a pending `.classification.json` are not listed; a later WatchPaths event retries.
2. For each file: read it, choose `pillar` ∈ {me, pulse, projects, intelligence, journey} and `confidence` ∈ [0,1]. No fit ⇒ `--pillar=none`.
3. `python3 script.py apply --file=<name> --pillar=<p> --confidence=<c> [--threshold=<t>] [--alternatives='[{"pillar":"pulse","confidence":0.2}]']`

Threshold: `--threshold` > `ingest-confidence: <0..1>` line under `## Thresholds` in `anatomy/preferences.md` > 0.7 (absent/invalid/missing file ⇒ 0.7, no error).

`apply` outcomes (JSON, exit 0): `archived` (+ `archived` path) · `kept` (confidence < threshold; file stays, `<name>.classification.json` written, rewritten on re-classification) · `skipped` (`locked` | `unstable`) · `error` (`UNSUPPORTED` | `UNCLASSIFIABLE` | `ARCHIVE_MISSING` | `ARCHIVE_FAILED`; file stays, `<name>.error.md` written). Exit 1: `INVALID_PATH`, `NOT_FOUND`, `INVALID_ARGS` (`--confidence`/`--threshold` outside [0,1], NaN included).

## Confirm / reject

Ask the user about each pending file (`python3 script.py status` → `{status, pending:[{file, sidecar}]}`), then:

- `python3 script.py confirm --file=<name> [--pillar=<p>]` → archives the current file (confidence 1.0, optional pillar override, collision suffix), writes `.ingest.json`, removes source + sidecar. Outcomes as `apply` (`archived` | `skipped` | `error`). Exit 1: `NOT_FOUND` (no sidecar), `INVALID_SIDECAR` (file stays), `INVALID_ARGS` (bad pillar), `INVALID_PATH`.
- `python3 script.py reject --file=<name>` → removes sidecar, writes `<name>.error.md` (`REJECTED`), file stays; outcome `rejected`. Exit 1: `NOT_FOUND`.

Sidecar `<name>.classification.json`: `proposal` (pillar), `confidence`, `threshold`, `alternatives[{pillar, confidence}]`, `proposed_at` (UTC ISO).

## Archive contract

Capability `gilberto-capability-<pillar>-archive` (found like `dispatch.sh`, dir under `*/skills/`) is run as `python3 script.py --source=<abs path> --pillar=<p> --name=<final name>`; it must create `$GILBERTO_ROOT/<pillar>/<name>` and exit 0. `<name>` is collision-free (`a.pdf` → `a-1.pdf`), never overwrites. On success ingest writes `<pillar>/<name>.ingest.json` (`source`, `pillar`, `confidence`, `ingested_at`) and removes the source from `_ingest/`.

Supported: pdf md txt html docx png jpg jpeg. One run at a time: `scan` records its parent (run) pid in `_ingest/.ingest.run`; another run's `scan` is `skipped` (`locked`) while that pid lives, a dead owner is stale. `apply` takes `_ingest/.ingest.lock` per file, non-blocking. Run scan and applies from the same parent process.
