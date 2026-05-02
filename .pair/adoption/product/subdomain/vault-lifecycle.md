# Vault Lifecycle (Supporting Subdomain)

> Classification: **Supporting**

**Business Purpose:**
Manage a Gilberto instance's lifecycle from birth to retirement: conversational bootstrap, safe upgrade with fork-on-write, backwards-incompatible shape migration, transportable export, archive of dismissed pillars/topics.

**Key Capabilities:**

- Conversational bootstrap after `gilberto install` (5 pillars + network + anatomy + `.envrc` + launchd plists) — `gilberto-process-vault-bootstrap`
- Upgrade pulls updated skills+anatomy while preserving customisations — `gilberto-process-vault-upgrade`
- Shape migration with mandatory dry-run + pre-migration snapshot — `gilberto-process-vault-migrate`
- Transportable snapshot export (tar/zip + checksum) — `gilberto-process-vault-export`
- Archive of inactive pillars/topics (`_archive/<original-path>/`) — `gilberto-process-vault-archive`
- Mechanic primitives (`mechanic-vault-{new,promote,collapse}`) for structural scaffolding

**Strategic Importance:**
Necessary for the framework to function but not where the user-perceived value lives. Every framework has installer/migrator. Quality is an *enabler* — bootstrap >5 min kills adoption (PRD §4 KPI <5 min).

**Complexity Assessment:**
Medium — diff/merge between core anatomy and customisations (fork-on-write), versioned migration scripts, snapshot/rollback safety, idempotency for re-runs.

**Data Ownership:**
Skills `gilberto-process-vault-*` (5) + `mechanic-vault-*`. `_archive/` directory. Migration scripts under `anatomy/migrations/`. Pre-upgrade snapshot as a temporary tarball.

**Dependencies:**

- Depends on: Distribution & Onboarding (CLI `gilberto install/update` invokes these processes), Adaptive Anatomy (scaffolding templates read at bootstrap; versioning for migration)
- Provides to: Personal Knowledge Graph (materialises the structure), Cognitive Operations + Plugin Ecosystem (reuse mechanic primitives at runtime)

**Team Recommendations:**
Single-contributor in v1. Profile: system-engineer (diff/merge, snapshot, idempotency). Temp-dir test matrix (CLAUDE.md §Testing). Tightly coordinated with Distribution for install UX.

**Implementation Priority:**
High for bootstrap+upgrade (PRD Phases 1-4: M1, M5-M6); Medium for migrate+archive (post-v1, when real migrations emerge); Low for export (P2 backup feature).
