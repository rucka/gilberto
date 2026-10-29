---
'gilberto': minor
'@foomakers/gilberto-vault-bootstrap': minor
---

Wizard step 4: materialize the vault skeleton (5 pillars, `network/`, `anatomy/`, `_ingest/`, root `CLAUDE.md`, per-topic folder-notes) in `$TMPDIR/gilberto-install-<pid>/`, then atomic rename to the target; rollback on error/SIGINT (exit 130). `vault-bootstrap` exports `renderPillarNote`/`renderTopicNote`.
