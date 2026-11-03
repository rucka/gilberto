import importlib.util
import json
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("archive_helpers", Path(__file__).resolve().parent / "archive_helpers.py")
_helpers = importlib.util.module_from_spec(_spec)
sys.modules["archive_helpers"] = _helpers  # by name, not sys.path: a path entry would shadow sibling skills' `conftest`
_spec.loader.exec_module(_helpers)
SCRIPT, TEMPLATE, TOPICS, tree = _helpers.SCRIPT, _helpers.TEMPLATE, _helpers.TOPICS, _helpers.tree


@pytest.fixture
def avault(tmp_path):
    root = tmp_path / "vault"
    for d in ("me", "pulse", "projects", "intelligence", "journey", "network"):
        (root / d).mkdir(parents=True)
    tpl = root / "anatomy/templates/intelligence/note"
    tpl.mkdir(parents=True)
    (tpl / "note.md").write_text(TEMPLATE)
    (root / "anatomy/topics.md").write_text(TOPICS)
    src = root / "anatomy/playbooks/intelligence/sources"
    src.mkdir(parents=True)
    (src / "acme.md").write_text("---\ntype: anatomy-sources\n---\n")
    return root


@pytest.fixture
def snap():
    return tree


@pytest.fixture
def archive(capsys, avault):
    """archive(*argv) -> (exit code, stdout JSON, stderr); in-process."""
    spec = importlib.util.spec_from_file_location("archive_cap", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def run(*argv):
        capsys.readouterr()
        code = mod.main(list(argv), {"GILBERTO_ROOT": str(avault)})
        out = capsys.readouterr()
        return code, json.loads(out.out), out.err

    return run
