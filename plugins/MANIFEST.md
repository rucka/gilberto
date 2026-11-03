# Plugin manifest

Each plugin ships `.claude-plugin/plugin.json`. Anthropic keys stay top-level; gilberto fields live under the single `gilberto` key (strict: unknown keys rejected). Paths are relative to the plugin dir.

| Key                      | Type                    | Notes                                                                          |
| ------------------------ | ----------------------- | ------------------------------------------------------------------------------ |
| `name`, `description`    | string, required        |                                                                                |
| `author`                 | `{ name }`, optional    |                                                                                |
| `skills`                 | string[], default `[]`  | skill dirs; no duplicate name/path; each must exist                            |
| `gilberto.kind`          | enum: core, pillar, connector | required                                                                       |
| `gilberto.pillar`        | string                  | required iff `kind` is `pillar`, forbidden otherwise                           |
| `gilberto.playbooks`     | `{ "<pillar>/<event>": path }` | pillar segment must equal `gilberto.pillar` when set                    |
| `gilberto.templates`, `processes`, `capabilities` | string[] | optional                                                      |
| `gilberto.preferences`   | string                  | optional                                                                       |
| `gilberto.routes`        | `{ key: value }`        | optional                                                                       |

Validation (`validateManifest(dir)`, pure): schema → duplicate skill → pillar mismatch → skills paths exist.

## Example

```json
{
  "name": "pulse-health-tracking",
  "description": "Health tracking for the pulse pillar.",
  "author": { "name": "rucka" },
  "skills": ["./skills/pulse-capability-log"],
  "gilberto": {
    "kind": "pillar",
    "pillar": "pulse",
    "templates": ["./templates/pulse"],
    "playbooks": { "pulse/daily": "./playbooks/pulse/daily/health.md" },
    "preferences": "./preferences.md",
    "routes": { "health": "pulse" }
  }
}
```
