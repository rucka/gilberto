import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"
FM = {"type": "project-index", "topics": ["growth"], "status": "active"}


def args(**over):
    a = {"pillar": "projects", "template": "generic", "slug": "alpha", "frontmatter": json.dumps(FM)}
    a.update(over)
    return [f"--{k}={v}" for k, v in a.items()]


def test_ac1_creates_entity(mechanic, vault):
    code, out, _ = mechanic("new", *args())
    assert code == 0 and out["status"] == "ok" and out["errors"] == []
    note = vault / "projects/alpha/alpha.md"
    text = note.read_text()
    today = re.escape(__import__("datetime").date.today().isoformat())
    assert re.match(rf'---\ntype: "project-index"\ntopics: \["growth"\]\nstatus: "active"\ncreated: "{today}"\nupdated: "{today}"\n---\n', text)
    assert "# {{title}}\n\nbody" in text
    assert json.loads((vault / "projects/alpha/.alpha.json").read_text())["slug"] == "alpha"
    assert sorted(out["written"]) == ["projects/alpha", "projects/alpha/.alpha.json", "projects/alpha/alpha.md"]
    assert not [p for p in vault.rglob("*.tmp.*")]


def test_ac2_idempotent(mechanic, vault, tree):
    mechanic("new", *args())
    before = tree(vault)
    code, out, err = mechanic("new", *args())
    assert code == 0 and out["status"] == "skipped" and out["written"] == []
    assert out["skipped"] == ["projects/alpha/alpha.md"] and "skipped (idempotent)" in err
    assert tree(vault) == before


def test_force_rewrites_frontmatter_only(mechanic, vault):
    mechanic("new", *args())
    note = vault / "projects/alpha/alpha.md"
    text = note.read_text().replace("body", "EDITED body")
    note.write_text(re.sub(r'created: ".*"', 'created: "2000-01-01"', text))
    fm = dict(FM, topics=["new"])
    code, out, _ = mechanic("new", *args(frontmatter=json.dumps(fm)), "--force")
    assert code == 0 and out["status"] == "ok"
    new = note.read_text()
    assert 'topics: ["new"]' in new and "EDITED body" in new and 'created: "2000-01-01"' in new


def test_ac6_invalid_slug(mechanic, vault, tree):
    before = tree(vault)
    for bad in ("../x", "..\\x", "/abs", "Upper", "a b", "é", "-x", "a" * 65):
        code, out, _ = mechanic("new", *args(slug=bad))
        assert code == 1 and out["errors"] == [{"code": "INVALID_SLUG", "input": bad}]
    assert tree(vault) == before


def test_ac7_pillar_not_found(mechanic, vault, tree):
    before = tree(vault)
    code, out, _ = mechanic("new", *args(pillar="ghost"))
    assert code == 1 and out["errors"] == [{"code": "PILLAR_NOT_FOUND", "pillar": "ghost"}]
    assert tree(vault) == before


def test_missing_template(mechanic, vault):
    code, out, _ = mechanic("new", *args(template="nope"))
    assert code == 1 and out["errors"][0]["code"] == "TEMPLATE_NOT_FOUND"
    code, out, _ = mechanic("new", *args(template="../x"))
    assert out["errors"][0]["code"] == "INVALID_SLUG"


@pytest.mark.parametrize(
    "fm",
    [{"type": "project-index"}, {**FM, "type": "weird-thing"}, {**FM, "extra": 1}, "not json", "[1]"],
)
def test_invalid_frontmatter(mechanic, vault, tree, fm):
    before = tree(vault)
    code, out, _ = mechanic("new", *args(frontmatter=fm if isinstance(fm, str) else json.dumps(fm)))
    assert code == 1 and out["errors"][0]["code"] == "INVALID_FRONTMATTER"
    assert tree(vault) == before


def test_anatomy_diff_reported(mechanic, vault):
    code, out, _ = mechanic("new", *args(frontmatter=json.dumps({"type": "project-index", "topics": []})))
    assert out["errors"][0]["diff"] == {"missing": ["status"], "unknown": []}


def test_missing_arg(mechanic):
    code, out, _ = mechanic("new", "--pillar=projects")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_ARGS"


def test_symlinked_pillar_rejected(mechanic, vault, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (vault / "me").rmdir()
    os.symlink(outside, vault / "me")
    code, out, _ = mechanic("new", *args(pillar="me"))
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH"
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("fail_on", [1, 2])
def test_ac8_rollback_and_retry(mechanic, vault, tree, monkeypatch, fail_on):
    before = tree(vault)
    real, calls = os.replace, {"n": 0}

    def flaky(a, b):
        calls["n"] += 1
        if calls["n"] == fail_on:
            raise OSError(5, "EIO")
        return real(a, b)

    monkeypatch.setattr(os, "replace", flaky)
    code, out, _ = mechanic("new", *args())
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED"
    assert tree(vault) == before  # no folder, note, sidecar or tmp orphan
    monkeypatch.setattr(os, "replace", real)
    code, out, _ = mechanic("new", *args())
    assert code == 0 and (vault / "projects/alpha/alpha.md").exists()


def test_sigint_mid_write_cleans_up(mechanic, vault, tree, monkeypatch):
    before = tree(vault)

    def interrupt(a, b):
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "replace", interrupt)
    with pytest.raises(KeyboardInterrupt):
        mechanic("new", *args())
    assert tree(vault) == before


def test_subprocess_smoke(vault):
    env = {**os.environ, "GILBERTO_ROOT": str(vault)}
    p = subprocess.run([sys.executable, str(SCRIPT), *args()], capture_output=True, text=True, env=env)
    assert p.returncode == 0 and json.loads(p.stdout)["status"] == "ok"
    p2 = subprocess.run([sys.executable, str(SCRIPT), *args()], capture_output=True, text=True, env=env)
    assert json.loads(p2.stdout)["status"] == "skipped"
