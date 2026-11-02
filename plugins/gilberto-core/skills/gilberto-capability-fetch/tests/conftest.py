import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_helpers import SCRIPT  # noqa: E402


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
    mod.SKILLS = str(tmp_path / "core-skills")  # hermetic: real core utilities must not shadow fakes

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


FAKE = """import json, os, sys
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "args.json"), "w").write(json.dumps(sys.argv[1:]))
sys.stderr.write({stderr!r})
print({stdout!r})
sys.exit({code})
"""


@pytest.fixture
def utility(tmp_path):
    """utility(name, items=None, code=0, stdout=None, stderr='') installs a fake utility; -> dir it lives under (GILBERTO_UTILITY_PATH)."""
    base = tmp_path / "utilities"

    def install(name, items=(), code=0, stdout=None, stderr=""):
        d = base / name
        d.mkdir(parents=True, exist_ok=True)
        out = json.dumps({"items": list(items)}) if stdout is None else stdout
        (d / "script.py").write_text(FAKE.format(stdout=out, stderr=stderr, code=code))
        return str(base)

    install.args = lambda name: json.loads((base / name / "args.json").read_text())
    install.path = str(base)
    return install
