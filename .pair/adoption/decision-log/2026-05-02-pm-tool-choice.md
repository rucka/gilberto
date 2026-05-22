# ADL: PM Tool — GitHub Projects v2 (Kanban)

- **Date**: 2026-05-02
- **Status**: Accepted
- **Type**: non-architectural
- **Source**: `/pair-capability-setup-pm` (composed by `/pair-process-bootstrap` Phase 4.2)

## Decision

**GitHub Projects v2** is adopted as the project management tool, with **Kanban** methodology.

- **Project**: `gilberto roadmap` — <https://github.com/users/rucka/projects/2>
- **Owner scope**: user (`rucka`)
- **Linked repository**: `rucka/gilberto`
- **Methodology**: Kanban — continuous flow, no fixed sprints

## Rationale

- Type A pet project, single contributor, GitHub-centric development
- Free tier sufficient; no paid PM tool needed
- Native integration with GitHub Issues + PRs already used for development
- MCP `mcp__github__*` tools available for AI-assisted management
- Configuration aligned to `foomakers/pair` to maintain coherence with the reference framework

## Configuration

### Status (4 columns)

Todo · Refined · In Progress · Done. Review state is implicit via the built-in `Linked pull requests` field.

### Custom Fields

| Field | Type | Values |
|---|---|---|
| Priority | single-select | P0, P1, P2 |

No `Effort` field — story points (XS/S/M/L/XL) live in the story body (aligned to `foomakers/pair`).

### Repo Labels (`rucka/gilberto`)

- **Type**: `initiative`, `epic`, `user story`
- **Area**: `cli`, `dataset`, `website`, `plugin`, `docs`, `infra`

No `task` label — tasks are inline in user-story body.

### Workflow

| Transition | Trigger |
|---|---|
| Todo → Refined | `/pair-process-refine-story` complete |
| Refined → In Progress | `/pair-process-implement` start |
| In Progress → Done | PR merged + issue closed |

### Issue Hierarchy

Initiative → Epic → User Story via built-in `Parent issue` field. Tasks inline in story body.

## Alternatives Considered

- **Filesystem PM**: rejected — single-contributor doesn't need offline-first; loses GitHub-native PR linkage
- **Linear**: rejected — paid tier for full features; no benefit over GitHub Projects for solo dev
- **Jira / Azure DevOps**: rejected — over-engineered for Type A

## Implications

- Issues are the unit of work; tasks live in story body (created via `/pair-process-plan-tasks`)
- Project board status field is the source of truth for workflow state, separate from issue open/closed state
- Custom field updates use GraphQL mutations (see [github-implementation.md](../../knowledge/guidelines/collaboration/project-management-tool/github-implementation.md))

## References

- [`../tech/way-of-working.md`](../tech/way-of-working.md) §Project Management Tool
- [`../product/PRD.md`](../product/PRD.md) §10 — milestones / phase plan to be loaded into the board
- Reference project: `foomakers/pair` (foomakers org, project #3)
