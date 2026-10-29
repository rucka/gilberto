import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILLS))

TYPES_TABLE = """---
type: anatomy
created: '2026-01-01'
updated: '2026-01-01'
---

# Anatomy

## Types

| Type | Folder | Description | Fields |
| ---- | ------ | ----------- | ------ |
| project-index | projects | project | status |
| projects-index | projects | free type | |

## Relationship levels
"""

TEMPLATE = """---
type: project-index
topics: []
---

# {{title}}

body
"""


TOPICS = """---
type: anatomy-topics
---

# Topics

| Topic | Description |
| ----- | ----------- |
| health | body |

trailing prose
"""


@pytest.fixture
def vault(tmp_path):
    """Tmp vault: 5 pillars + network/ + anatomy/ (anatomy.md, topics.md, templates/projects/generic/generic.md)."""
    root = tmp_path / "vault"
    for d in ("me", "pulse", "projects", "intelligence", "journey", "network"):
        (root / d).mkdir(parents=True)
    tpl = root / "anatomy" / "templates" / "projects" / "generic"
    tpl.mkdir(parents=True)
    (tpl / "generic.md").write_text(TEMPLATE)
    (root / "anatomy" / "anatomy.md").write_text(TYPES_TABLE)
    (root / "anatomy" / "topics.md").write_text(TOPICS)
    return root


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes() if p.is_file() else None) for p in sorted(root.rglob("*"))}


@pytest.fixture
def tree():
    return snapshot


@pytest.fixture
def mechanic(capsys, vault):
    """mechanic(name, *argv, root=vault) -> (exit code, parsed stdout JSON); runs script.py in-process."""

    def run(name, *argv, root=None):
        folder = f"mechanic-{name}" if name.startswith("forge-") else f"mechanic-vault-{name}"
        path = SKILLS / folder / "script.py"
        spec = importlib.util.spec_from_file_location(f"mechanic_{name}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        capsys.readouterr()
        code = mod.main(list(argv), {"GILBERTO_ROOT": str(root or vault)})
        out = capsys.readouterr()
        return code, json.loads(out.out), out.err

    return run
