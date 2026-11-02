import importlib.util
import json
import os
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
SEED = HERE.parents[3] / "packages" / "vault-bootstrap" / "seed" / "anatomy" / "preferences.md"
spec = importlib.util.spec_from_file_location("ingest_seed_threshold_script", HERE / "script.py")
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    for d in ("me", "_ingest", "anatomy"):
        (root / d).mkdir(parents=True)
    arch = tmp_path / "plugins" / "p" / "skills" / "gilberto-capability-me-archive"
    arch.mkdir(parents=True)
    (arch / "script.py").write_text(
        "import argparse, os, shutil\n"
        "p = argparse.ArgumentParser()\n"
        'p.add_argument("--source"); p.add_argument("--pillar"); p.add_argument("--name")\n'
        "a = p.parse_args()\n"
        'shutil.copy(a.source, os.path.join(os.environ["GILBERTO_ROOT"], a.pillar, a.name))\n'
    )
    env = {"GILBERTO_ROOT": str(root), "GILBERTO_SKILLS_DIR": str(tmp_path / "plugins"), "HOME": str(tmp_path)}
    return root, env


def seed_with(root, value):
    text = SEED.read_text()
    assert "0.7" in text
    (root / "anatomy" / "preferences.md").write_text(text.replace("0.7", value))


def test_seed_edited_value_is_read(vault):
    root, _ = vault
    seed_with(root, "0.2")
    assert script._threshold(str(root), None) == 0.2


def test_seed_edited_value_drives_apply(vault, capsys):
    root, env = vault
    seed_with(root, "0.2")
    p = root / "_ingest" / "a.pdf"
    p.write_bytes(b"%PDF")
    t = time.time() - 60
    os.utime(p, (t, t))
    capsys.readouterr()
    script.main(["apply", "--file=a.pdf", "--pillar=me", "--confidence=0.3"], env)
    assert json.loads(capsys.readouterr().out)["status"] == "archived"
