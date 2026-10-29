import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"
BASE = "anatomy/templates/intelligence/interview-note"


def test_ac3_creates_template(mechanic, vault):
    code, out, _ = mechanic("forge-template", "--name=interview-note", "--pillar=intelligence", "--description=Interview")
    assert code == 0 and out["status"] == "ok" and out["errors"] == []
    assert (vault / BASE / "template.md").read_text() == (
        '---\nscope: "intelligence"\ndescription: "Interview"\n---\n\n# interview-note\n'
    )
    placeholder = (vault / BASE / "files/note.md").read_text()
    assert all(m in placeholder for m in ("{{SLUG}}", "{{TITLE}}", "{{DATE}}"))
    assert sorted(out["written"]) == sorted(
        [BASE, f"{BASE}/files", f"{BASE}/template.md", f"{BASE}/files/note.md"]
    )
    assert not list(vault.rglob("*.tmp.*"))


def test_idempotent(mechanic, vault, tree):
    mechanic("forge-template", "--name=interview-note", "--pillar=intelligence")
    before = tree(vault)
    code, out, err = mechanic("forge-template", "--name=interview-note", "--pillar=intelligence")
    assert code == 0 and out["status"] == "skipped" and out["written"] == []
    assert "skipped (idempotent)" in err and tree(vault) == before


def test_rerun_keeps_edited_template_and_heals_missing(mechanic, vault):
    mechanic("forge-template", "--name=interview-note", "--pillar=intelligence")
    (vault / BASE / "template.md").write_text("EDITED")
    (vault / BASE / "files/note.md").unlink()
    code, out, _ = mechanic("forge-template", "--name=interview-note", "--pillar=intelligence")
    assert out["written"] == [f"{BASE}/files/note.md"]
    assert (vault / BASE / "template.md").read_text() == "EDITED"


@pytest.mark.parametrize("bad", ["../x", "..\\x", "/abs", "Upper", "a b", "é", "-x", "a" * 65, "x\n"])
def test_ac6_invalid_slug(mechanic, vault, tree, bad):
    before = tree(vault)
    code, out, _ = mechanic("forge-template", f"--name={bad}", "--pillar=intelligence")
    assert code == 1 and out["errors"] == [{"code": "INVALID_SLUG", "input": bad}]
    assert tree(vault) == before


@pytest.mark.parametrize("bad", ["ghost", "anatomy", "../me", "Pulse"])
def test_invalid_pillar(mechanic, vault, tree, bad):
    before = tree(vault)
    code, out, _ = mechanic("forge-template", "--name=x", f"--pillar={bad}")
    assert code == 1 and out["errors"] == [{"code": "INVALID_PILLAR", "pillar": bad}]
    assert tree(vault) == before


def test_missing_arg(mechanic):
    code, out, _ = mechanic("forge-template", "--name=x")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_ARGS"


def test_symlinked_templates_dir_rejected(mechanic, vault, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (vault / "anatomy/templates/projects/generic/generic.md").unlink()
    (vault / "anatomy/templates/projects/generic").rmdir()
    (vault / "anatomy/templates/projects").rmdir()
    os.symlink(outside, vault / "anatomy/templates/projects")
    code, out, _ = mechanic("forge-template", "--name=x", "--pillar=projects")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH"
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("fail_on", [1, 2])
def test_rollback_and_retry(mechanic, vault, tree, monkeypatch, fail_on):
    before = tree(vault)
    real, calls = os.replace, {"n": 0}

    def flaky(a, b):
        calls["n"] += 1
        if calls["n"] == fail_on:
            raise OSError(5, "EIO")
        return real(a, b)

    monkeypatch.setattr(os, "replace", flaky)
    code, out, _ = mechanic("forge-template", "--name=interview-note", "--pillar=intelligence")
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED"
    assert tree(vault) == before
    monkeypatch.setattr(os, "replace", real)
    code, _, _ = mechanic("forge-template", "--name=interview-note", "--pillar=intelligence")
    assert code == 0 and (vault / BASE / "template.md").exists()


def test_subprocess_smoke_twice(vault):
    env = {**os.environ, "GILBERTO_ROOT": str(vault)}
    cmd = [sys.executable, str(SCRIPT), "--name=interview-note", "--pillar=intelligence"]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert p.returncode == 0 and json.loads(p.stdout)["status"] == "ok"
    p2 = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert json.loads(p2.stdout)["status"] == "skipped"
