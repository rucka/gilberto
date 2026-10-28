import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"
NOTE = '---\ntype: "projects-index"\ntopics: []\ncreated: "2020-01-01"\nupdated: "2020-01-01"\n---\n\nsee [[alpha]] and [[beta]]\n'


@pytest.fixture
def entity(vault):
    (vault / "projects/alpha.md").write_text(NOTE)
    (vault / "projects/beta.md").write_text("link [[alpha]]\n")
    return vault / "projects/alpha.md"


def test_ac3_promote(mechanic, vault, entity):
    code, out, _ = mechanic("promote", "--path=projects/alpha.md")
    assert code == 0 and out["status"] == "ok"
    new = vault / "projects/alpha/alpha.md"
    assert not entity.exists() and new.is_file()
    text = new.read_text()
    assert text.replace(text.split("updated: ")[1].split("\n")[0], '"2020-01-01"') == NOTE
    assert text.split("updated: ")[1].split("\n")[0] != '"2020-01-01"'
    assert "[[alpha]]" in text and (vault / "projects/beta.md").read_text() == "link [[alpha]]\n"
    assert out["written"] == ["projects/alpha", "projects/alpha/alpha.md"]


def test_ac4_already_promoted(mechanic, vault, entity, tree):
    mechanic("promote", "--path=projects/alpha.md")
    before = tree(vault)
    code, out, err = mechanic("promote", "--path=projects/alpha.md")
    assert code == 0 and out["status"] == "skipped" and "already promoted" in err
    assert tree(vault) == before


def test_missing_and_conflict(mechanic, vault, entity):
    code, out, _ = mechanic("promote", "--path=projects/ghost.md")
    assert code == 1 and out["errors"][0]["code"] == "ENTITY_NOT_FOUND"
    (vault / "projects/alpha").mkdir()
    (vault / "projects/alpha/alpha.md").write_text("x")
    code, out, _ = mechanic("promote", "--path=projects/alpha.md")
    assert code == 1 and out["errors"][0]["code"] == "CONFLICT"
    assert entity.read_text() == NOTE


def test_promote_into_existing_folder(mechanic, vault, entity):
    (vault / "projects/alpha").mkdir()
    (vault / "projects/alpha/other.md").write_text("o")
    code, _, _ = mechanic("promote", "--path=projects/alpha.md")
    assert code == 0 and (vault / "projects/alpha/other.md").read_text() == "o"


@pytest.mark.parametrize("bad", ["../x.md", "..\\x.md", "/projects/a.md", "projects/Alpha.md", "projects/a b.md", "projects/é.md", "projects/alpha"])
def test_ac6_invalid_slug(mechanic, vault, entity, tree, bad):
    before = tree(vault)
    code, out, _ = mechanic("promote", f"--path={bad}")
    assert code == 1 and out["errors"] == [{"code": "INVALID_SLUG", "input": bad}]
    assert tree(vault) == before


def test_pillar_and_symlink(mechanic, vault, tmp_path):
    code, out, _ = mechanic("promote", "--path=ghost/a.md")
    assert out["errors"][0]["code"] == "PILLAR_NOT_FOUND"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "a.md").write_text("x")
    os.symlink(outside, vault / "projects/evil")
    code, out, _ = mechanic("promote", "--path=projects/evil/a.md")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH"
    assert (outside / "a.md").read_text() == "x"


def test_missing_arg(mechanic):
    assert mechanic("promote")[1]["errors"][0]["code"] == "INVALID_ARGS"


def test_rollback_when_move_fails(mechanic, vault, entity, tree, monkeypatch):
    before = tree(vault)
    real = os.replace

    def boom(a, b):
        raise OSError(5, "EIO")

    monkeypatch.setattr(os, "replace", boom)
    code, out, _ = mechanic("promote", "--path=projects/alpha.md")
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED"
    assert tree(vault) == before
    monkeypatch.setattr(os, "replace", real)
    assert mechanic("promote", "--path=projects/alpha.md")[0] == 0


def test_rollback_when_unlink_fails(mechanic, vault, entity, tree, monkeypatch):
    before = tree(vault)
    real = os.unlink

    def unlink(p):
        if p == str(entity.resolve()):
            raise OSError(5, "EIO")
        real(p)

    monkeypatch.setattr(os, "unlink", unlink)
    code, out, _ = mechanic("promote", "--path=projects/alpha.md")
    assert code == 1 and tree(vault) == before


def test_subprocess_smoke(vault, entity):
    env = {**os.environ, "GILBERTO_ROOT": str(vault)}
    p = subprocess.run([sys.executable, str(SCRIPT), "--path=projects/alpha.md"], capture_output=True, text=True, env=env)
    assert p.returncode == 0 and json.loads(p.stdout)["status"] == "ok"
