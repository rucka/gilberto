# ADL — Public tools, private content

**Date:** 2026-11-02
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** repo contents, migration tooling (#14, #19, #24), owner-personal plugins (#3, #4)

## Context

Backlog mixed generic capabilities with the owner's personal data and apps (my-intelligence paths/topics, Ratko, health). Public repo must stay reusable and free of personal content.

## Decision

- `rucka/gilberto` ships tools only: procedures, skills, generic configurable import/migration scripts.
- Never personal content: no owner paths, topic names, data or credentials baked in. Owner specifics may appear only as example config in docs.
- Personal data imported by running those tools on the owner's vault instance; per-source decisions (include/exclude, topic mapping) live in the personal config.
- Import tools: source path + include/exclude/topic-mapping config, dry-run + diff report, hard deny-list for secret-like files (`credentials*.json`, `*.pem`, `.env*`, keys).
- Owner-personal apps/data (e.g. Ratko, finance, health) = private plugins, possibly one private repo holding all, installed only on the personal instance via plugin protocol (#15).
- Running a migration on real content is an operational step on the personal instance, not a repo story.

## Consequences

- #128 closed not planned; #124-#127 reworded generic.
- #3/#4 epics carrying personal apps annotated: personal parts delivered as private plugins outside repo.

## References

- [PRD](../product/PRD.md) · [architecture.md](../tech/architecture.md) · [ADR-0002](../tech/adr/0002-distribution-and-dual-entry-bootstrap.md)
