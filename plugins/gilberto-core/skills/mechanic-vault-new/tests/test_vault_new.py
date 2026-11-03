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


def test_ac6_trailing_newline_slug(mechanic, vault, tree):
    before = tree(vault)
    code, out, _ = mechanic("new", *args(slug="alpha\n"))
    assert code == 1 and out["errors"] == [{"code": "INVALID_SLUG", "input": "alpha\n"}]
    assert tree(vault) == before


def test_ac6_trailing_newline_template(mechanic, vault, tree):
    before = tree(vault)
    code, out, _ = mechanic("new", *args(template="generic\n"))
    assert code == 1 and out["errors"] == [{"code": "INVALID_SLUG", "input": "generic\n"}]
    assert tree(vault) == before


def test_trailing_newline_frontmatter_type(mechanic, vault, tree):
    before = tree(vault)
    code, out, _ = mechanic("new", *args(frontmatter=json.dumps(dict(FM, type="projects-index\n"))))
    assert code == 1 and out["errors"] == [
        {"code": "INVALID_FRONTMATTER", "type": "projects-index\n", "reason": "unknown type scope"}
    ]
    assert tree(vault) == before


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


def _intel(vault):
    tpl = vault / "anatomy/templates/intelligence/note"
    tpl.mkdir(parents=True)
    (tpl / "note.md").write_text('---\ntype: intelligence-note\ntopics: []\n---\n\n# {{title}}\n')


def nargs(path="health/acme", **over):
    return args(pillar="intelligence", template="note", slug="e1", frontmatter=json.dumps({"topics": ["health"]}), path=path, **over)


def test_path_writes_nested_note(mechanic, vault):
    _intel(vault)
    code, out, _ = mechanic("new", *nargs())
    assert code == 0 and out["status"] == "ok"
    assert (vault / "intelligence/health/acme/e1.md").is_file()
    assert not (vault / "intelligence/health/acme/.e1.json").exists()
    assert sorted(out["written"]) == [
        "intelligence/health",
        "intelligence/health/acme",
        "intelligence/health/acme/e1.md",
    ]


def test_path_idempotent(mechanic, vault, tree):
    _intel(vault)
    mechanic("new", *nargs())
    before = tree(vault)
    code, out, _ = mechanic("new", *nargs())
    assert code == 0 and out["skipped"] == ["intelligence/health/acme/e1.md"] and tree(vault) == before


@pytest.mark.parametrize("bad", ["../x", "health/../..", "a//b", "/abs", "health/Acme", "health/", "a/b/c", "health/_x", "_uncategorized/_x"])
def test_path_invalid_segments(mechanic, vault, tree, bad):
    _intel(vault)
    before = tree(vault)
    code, out, _ = mechanic("new", *nargs(path=bad))
    assert code == 1 and out["errors"][0]["code"] == "INVALID_SLUG"
    assert tree(vault) == before


def test_path_uncategorized_first_segment(mechanic, vault):
    _intel(vault)
    code, _, _ = mechanic("new", *nargs(path="_uncategorized/acme"))
    assert code == 0 and (vault / "intelligence/_uncategorized/acme/e1.md").is_file()


def test_path_symlink_escape_rejected(mechanic, vault, tmp_path, tree):
    _intel(vault)
    out_dir = tmp_path / "outside"
    out_dir.mkdir()
    (vault / "intelligence/health").symlink_to(out_dir)
    code, out, _ = mechanic("new", *nargs())
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH" and not list(out_dir.iterdir())


def test_path_rollback_removes_created_dirs(mechanic, vault, tree, monkeypatch):
    _intel(vault)
    before = tree(vault)
    import _lib.atomic_write as aw

    def boom(path, data):
        raise OSError("disk full")

    monkeypatch.setattr(aw, "atomic_write", boom)
    code, out, _ = mechanic("new", *nargs())
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED" and tree(vault) == before


def test_no_path_default_unchanged(mechanic, vault):
    code, out, _ = mechanic("new", *args())
    assert code == 0 and (vault / "projects/alpha/.alpha.json").is_file()
