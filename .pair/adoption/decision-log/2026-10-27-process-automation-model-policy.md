# Decision: Process automation + model/effort per delivery-cycle stage

## Date

2026-10-27

## Status

Active

## Category

Process Decision

## Context

Project on pair 0.5.2 with no automation config: no `automation.md`, no `risk-matrix.md`, no `workflowProfiles`. Delivery cycle ran on engine defaults. Need unattended runs and model/effort tuned per stage.

## Decision

- **Autonomy**: `preset: escalate-red` — prepare auto, merge auto except `risk:red`, `until: merged`.
- **Harness**: `claude-code`.
- **Model Policy**: `risk:green` cheap, `risk:yellow` balanced, `risk:red` frontier.
- **Tag Projection**: `Active: risk`. No Criticality Table (absent ⇒ Medium default; a table would make unlisted deployables High).
- **Workflow profile** `economico` (default, `pair.config.json`):

| Stage | Model | Effort | Context |
| --- | --- | --- | --- |
| contract | haiku | low | fresh |
| prepare | sonnet | medium | reuse |
| validate | sonnet | high | fresh |
| implement | sonnet | medium | fresh |
| green | sonnet | medium | reuse |
| verify | opus | medium | fresh |
| merge | sonnet | low | fresh |

- **Agent frontmatter** `.claude/agents/pair-*.md`: `effort` set per role, `pair-reviewer` model `opus`. In-session effort is otherwise only a prompt request.

## Alternatives Considered

- **supervised / full preset**: too manual / merges `risk:red` unattended.
- **Pilot KB mapping** (opus on prepare/validate): costlier; judgment kept on opus only at verify.
- **green effort low**: risks extra remediation rounds on behavioral cards; revisit if cards are doc-only.
- **Frontier everywhere**: maximum cost.

## Consequences

- Frontmatter edits are overwritten by `pair update`; reapply after each update.
- `CLAUDE.md` start block `/next` → `/pair-next` fix is also lost on update.
- Revisit `green` to low if rounds stay low on doc-only cards; to balanced/high if behavioral cards need extra rounds.

## Adoption Impact

- `adoption/tech/automation.md` (new): `## Autonomy`, `## Harness`, `## Model Policy`, `## Working Cleanup`.
- `adoption/tech/risk-matrix.md` (new): `## Tag Projection`.
- `adoption/tech/workflow-profiles/economico.json` (new) + `pair.config.json` (new, `workflowProfiles`).
