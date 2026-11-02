import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"


def load():
    spec = importlib.util.spec_from_file_location("capability_fetch", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def fetch(capsys, tmp_path, monkeypatch):
    """fetch(*argv) -> (exit code, stdout JSON, stderr); runs script.py main in-process on tmp vault `fetch.root`."""
    root = tmp_path / "vault"
    root.mkdir()
    mod = load()

    def run(*argv, env=None):
        capsys.readouterr()
        code = mod.main(list(argv), {"GILBERTO_ROOT": str(root), **(env or {})})
        out = capsys.readouterr()
        return code, json.loads(out.out), out.err

    run.root = root
    run.mod = mod
    return run


@pytest.fixture
def source(fetch):
    """source(pillar, contributor, *blocks) writes anatomy/playbooks/<pillar>/sources/<contributor>.md."""

    def write(pillar, contributor, *blocks, raw=None):
        f = fetch.root / "anatomy/playbooks" / pillar / "sources" / f"{contributor}.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(raw if raw is not None else "---\ntype: anatomy-sources\n---\n\n# Sources\n\n" + "\n".join(blocks))
        return f

    return write
