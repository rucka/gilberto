import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"
NOTE = '---\ntype: "projects-index"\ntopics: []\ncreated: "2020-01-01"\nupdated: "2020-01-01"\n---\n\nsee [[alpha]]\n'


@pytest.fixture
def folder(vault):
    d = vault / "projects/alpha"
    d.mkdir()
    (d / "alpha.md").write_text(NOTE)
    return d


def test_ac5_collapse(mechanic, vault, folder):
    code, out, _ = mechanic("collapse", "--path=projects/alpha")
    assert code == 0 and out["status"] == "ok"
    assert not folder.exists()
    text = (vault / "projects/alpha.md").read_text()
    assert text.startswith("---\ntype") and "see [[alpha]]\n" in text
    assert 'updated: "2020-01-01"' not in text and 'created: "2020-01-01"' in text
    assert out["written"] == ["projects/alpha.md"]


def test_sidecar_is_not_a_child_and_is_removed(mechanic, vault, folder):
    (folder / ".alpha.json").write_text("{}")
    code, _, _ = mechanic("collapse", "--path=projects/alpha")
    assert code == 0 and not folder.exists()


@pytest.mark.parametrize("child", ["extra.md", ".hidden", ".other.json", "sub"])
def test_ac5_has_children(mechanic, vault, folder, tree, child):
    (folder / ".alpha.json").write_text("{}")
    c = folder / child
    c.mkdir() if child == "sub" else c.write_text("x")
    before = tree(vault)
    code, out, _ = mechanic("collapse", "--path=projects/alpha")
    assert code == 1
    assert out["errors"] == [{"code": "HAS_CHILDREN", "children": [child]}]
    assert tree(vault) == before


def test_already_collapsed(mechanic, vault, tree):
    (vault / "projects/alpha.md").write_text(NOTE)
    before = tree(vault)
    code, out, err = mechanic("collapse", "--path=projects/alpha")
    assert code == 0 and out["status"] == "skipped" and "already collapsed" in err
    assert tree(vault) == before


def test_missing_conflict(mechanic, vault, folder):
    assert mechanic("collapse", "--path=projects/ghost")[1]["errors"][0]["code"] == "ENTITY_NOT_FOUND"
    (vault / "projects/alpha.md").write_text("x")
    assert mechanic("collapse", "--path=projects/alpha")[1]["errors"][0]["code"] == "CONFLICT"
    (vault / "projects/alpha.md").unlink()
    (folder / "alpha.md").unlink()
    assert mechanic("collapse", "--path=projects/alpha")[1]["errors"][0]["code"] == "ENTITY_NOT_FOUND"


def test_promote_collapse_roundtrip(mechanic, vault):
    (vault / "projects/alpha.md").write_text(NOTE)
    assert mechanic("promote", "--path=projects/alpha.md")[0] == 0
    assert mechanic("collapse", "--path=projects/alpha")[0] == 0
    assert (vault / "projects/alpha.md").read_text().endswith("see [[alpha]]\n")
    assert not (vault / "projects/alpha").exists()


@pytest.mark.parametrize("bad", ["../x", "..\\x", "/projects/a", "projects/Alpha", "projects/a b", "projects/é", "projects/alpha.md"])
def test_ac6_invalid_slug(mechanic, vault, folder, tree, bad):
    before = tree(vault)
    code, out, _ = mechanic("collapse", f"--path={bad}")
    assert code == 1 and out["errors"] == [{"code": "INVALID_SLUG", "input": bad}]
    assert tree(vault) == before


def test_pillar_symlink_args(mechanic, vault, tmp_path):
    assert mechanic("collapse", "--path=ghost/a")[1]["errors"][0]["code"] == "PILLAR_NOT_FOUND"
    outside = tmp_path / "outside"
    (outside / "a").mkdir(parents=True)
    (outside / "a" / "a.md").write_text("x")
    os.symlink(outside, vault / "projects/evil")
    code, out, _ = mechanic("collapse", "--path=projects/evil/a")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH"
    assert (outside / "a" / "a.md").exists()
    assert mechanic("collapse")[1]["errors"][0]["code"] == "INVALID_ARGS"


def test_rollback_on_write_failure(mechanic, vault, folder, tree, monkeypatch):
    before = tree(vault)
    real = os.replace
    monkeypatch.setattr(os, "replace", lambda a, b: (_ for _ in ()).throw(OSError(5, "EIO")))
    code, out, _ = mechanic("collapse", "--path=projects/alpha")
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED" and tree(vault) == before
    monkeypatch.setattr(os, "replace", real)
    assert mechanic("collapse", "--path=projects/alpha")[0] == 0


def test_note_restored_when_rmdir_fails(mechanic, vault, folder, tree, monkeypatch):
    before = tree(vault)

    def boom(p):
        raise OSError(5, "EIO")

    monkeypatch.setattr(os, "rmdir", boom)
    code, out, _ = mechanic("collapse", "--path=projects/alpha")
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED"
    assert tree(vault) == before


def test_note_preserved_when_rmdir_interrupted(mechanic, vault, folder, tree, monkeypatch):
    before = tree(vault)
    note = (folder / "alpha.md").read_bytes()

    def boom(p):
        raise KeyboardInterrupt()

    monkeypatch.setattr(os, "rmdir", boom)
    with pytest.raises(KeyboardInterrupt):
        mechanic("collapse", "--path=projects/alpha")
    assert tree(vault) == before
    assert (folder / "alpha.md").read_bytes() == note and not (vault / "projects/alpha.md").exists()


@pytest.mark.parametrize("sidecar", [False, True])
def test_note_preserved_when_interrupted_after_rmdir_completed(mechanic, vault, folder, tree, monkeypatch, sidecar):
    if sidecar:
        (folder / ".alpha.json").write_text('{"slug": "alpha"}')
    before = tree(vault)
    real = os.rmdir

    def late(p):
        real(p)
        raise KeyboardInterrupt()

    monkeypatch.setattr(os, "rmdir", late)
    with pytest.raises(KeyboardInterrupt):
        mechanic("collapse", "--path=projects/alpha")
    assert tree(vault) == before
    assert (folder / "alpha.md").read_text() == NOTE and not (vault / "projects/alpha.md").exists()
    assert (folder / ".alpha.json").exists() == sidecar


@pytest.mark.parametrize("exc", [OSError(5, "EIO"), KeyboardInterrupt()])
def test_sidecar_and_note_restored_when_rmdir_fails(mechanic, vault, folder, tree, monkeypatch, exc):
    (folder / ".alpha.json").write_text('{"slug": "alpha"}')
    before = tree(vault)

    def boom(p):
        raise exc

    monkeypatch.setattr(os, "rmdir", boom)
    try:
        code, out, _ = mechanic("collapse", "--path=projects/alpha")
        assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED"
    except KeyboardInterrupt:
        assert isinstance(exc, KeyboardInterrupt)
    assert tree(vault) == before
    assert (folder / "alpha.md").read_text() == NOTE and not (vault / "projects/alpha.md").exists()


@pytest.mark.parametrize("exc", [OSError(5, "EIO"), KeyboardInterrupt()])
def test_note_restored_when_sidecar_unlink_fails(mechanic, vault, folder, tree, monkeypatch, exc):
    (folder / ".alpha.json").write_text('{"slug": "alpha"}')
    before = tree(vault)
    real = os.unlink

    def flaky(p, *a, **k):
        if os.path.basename(os.fspath(p)) == ".alpha.json":
            raise exc
        return real(p, *a, **k)

    monkeypatch.setattr(os, "unlink", flaky)
    try:
        code, out, _ = mechanic("collapse", "--path=projects/alpha")
        assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED"
    except KeyboardInterrupt:
        assert isinstance(exc, KeyboardInterrupt)
    assert tree(vault) == before
    assert (folder / "alpha.md").read_text() == NOTE and (folder / ".alpha.json").exists()
    assert not (vault / "projects/alpha.md").exists()


def test_ac6_trailing_newline_slug(mechanic, vault, folder, tree):
    before = tree(vault)
    code, out, _ = mechanic("collapse", "--path=projects/alpha\n")
    assert code == 1 and out["errors"] == [{"code": "INVALID_SLUG", "input": "projects/alpha\n"}]
    assert tree(vault) == before


def test_subprocess_smoke(vault, folder):
    env = {**os.environ, "GILBERTO_ROOT": str(vault)}
    p = subprocess.run([sys.executable, str(SCRIPT), "--path=projects/alpha"], capture_output=True, text=True, env=env)
    assert p.returncode == 0 and json.loads(p.stdout)["status"] == "ok"
