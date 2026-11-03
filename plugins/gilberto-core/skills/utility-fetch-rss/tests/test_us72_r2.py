import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from rss_helpers import URL, fixture

SKILLS = Path(__file__).resolve().parents[2]
SITECUSTOMIZE = """import os, urllib.request


class R:
    def read(self, n=-1):
        return open(os.environ["RSS_FIXTURE"], "rb").read()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


urllib.request.urlopen = lambda req, timeout=None: R()
"""
ARCHIVE = """import argparse, os, shutil
p = argparse.ArgumentParser()
p.add_argument("--source"); p.add_argument("--pillar"); p.add_argument("--name")
a = p.parse_args()
dest = os.path.join(os.environ["GILBERTO_ROOT"], a.pillar, a.name)
os.makedirs(os.path.dirname(dest), exist_ok=True)
shutil.copy(a.source, dest)
"""


def _load(folder, alias):
    spec = importlib.util.spec_from_file_location(alias, SKILLS / folder / "script.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    for d in ("intelligence", "_ingest"):
        (root / d).mkdir(parents=True)
    return root


@pytest.fixture
def env(tmp_path, vault):
    stub = tmp_path / "stub"
    stub.mkdir()
    (stub / "sitecustomize.py").write_text(SITECUSTOMIZE)
    arch = tmp_path / "plugins" / "p" / "skills" / "gilberto-capability-intelligence-archive"
    arch.mkdir(parents=True)
    (arch / "script.py").write_text(ARCHIVE)
    feed = tmp_path / "feed.xml"
    feed.write_bytes(fixture("feed.xml"))
    return {
        "GILBERTO_ROOT": str(vault),
        "GILBERTO_SKILLS_DIR": str(tmp_path / "plugins"),
        "HOME": str(tmp_path / "home"),
        "PYTHONPATH": str(stub),
        "RSS_FIXTURE": str(feed),
    }


def _ingest(env, capsys, *argv):
    ing = _load("gilberto-process-ingest", "ingest_us72_r2")
    capsys.readouterr()
    code = ing.main(list(argv), env)
    return code, json.loads(capsys.readouterr().out)


def _apply(env, capsys, name):
    return _ingest(env, capsys, "apply", f"--file={name}", "--pillar=intelligence", "--confidence=0.95", "--min-age=0")


def _keep(vault, name="keep.md"):
    keep = vault / "notes" / name
    keep.parent.mkdir(exist_ok=True)
    keep.write_text("keep\n")
    return keep


def test_us72_r2_symlinked_file_outside_ingest_rejected(vault, env, capsys):  # r1-5
    keep = _keep(vault)
    (vault / "_ingest" / "link.md").symlink_to(keep)
    code, out = _apply(env, capsys, "link.md")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH", out
    assert keep.read_text() == "keep\n"


def test_us72_r2_symlinked_subdir_outside_ingest_rejected(vault, env, capsys):  # r1-5 interaction
    keep = _keep(vault, "x.md")
    (vault / "_ingest" / "intelligence").symlink_to(keep.parent, target_is_directory=True)
    code, out = _apply(env, capsys, "intelligence/x.md")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH", out
    assert keep.read_text() == "keep\n"


def test_us72_r2_symlinked_file_in_subdir_rejected(vault, env, capsys):  # r1-5 sub-file
    keep = _keep(vault)
    sub = vault / "_ingest" / "intelligence"
    sub.mkdir()
    (sub / "l.md").symlink_to(keep)
    code, out = _apply(env, capsys, "intelligence/l.md")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH", out
    assert keep.read_text() == "keep\n"


def _linked_with_sidecar(vault):
    keep = _keep(vault)
    side = keep.parent / "keep.md.classification.json"
    side.write_text(json.dumps({"proposal": "intelligence"}) + "\n")
    (vault / "_ingest" / "link.md").symlink_to(keep)
    return keep, side


def test_us72_r2_confirm_symlinked_file_rejected(vault, env, capsys):  # r1-5 consumer
    keep, side = _linked_with_sidecar(vault)
    code, out = _ingest(env, capsys, "confirm", "--file=link.md")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH", out
    assert keep.read_text() == "keep\n" and side.is_file()


def test_us72_r2_reject_symlinked_file_rejected(vault, env, capsys):  # r1-5 consumer
    keep, side = _linked_with_sidecar(vault)
    code, out = _ingest(env, capsys, "reject", "--file=link.md")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH", out
    assert keep.read_text() == "keep\n" and side.is_file()


def test_us72_r2_regular_ingest_file_archived(vault, env, capsys):  # r1-5 control
    (vault / "_ingest" / "a.md").write_text("a\n")
    code, out = _apply(env, capsys, "a.md")
    assert code == 0 and out["status"] == "archived" and (vault / "intelligence" / "a.md").is_file(), out


def test_us72_r2_regular_subdir_file_archived(vault, env, capsys):  # r1-5 control
    sub = vault / "_ingest" / "intelligence"
    sub.mkdir()
    (sub / "b.md").write_text("b\n")
    code, out = _apply(env, capsys, "intelligence/b.md")
    assert code == 0 and out["status"] == "archived" and (vault / "intelligence" / "b.md").is_file(), out
    assert not (sub / "b.md").exists()


def test_us72_r2_capability_rerun_after_ingest_cleared_reports_consistent(vault, env, capsys):  # r1-6
    cap = _load("gilberto-capability-fetch", "cap_us72_r2")
    src = vault / "anatomy/playbooks/intelligence/sources/core.md"
    src.parent.mkdir(parents=True)
    src.write_text(f'---\ntype: anatomy-sources\n---\n\n```yaml\n"{URL}":\n  type: rss\n```\n')
    assert cap.main([], env) == 0
    shutil.rmtree(vault / "_ingest" / "intelligence")
    capsys.readouterr()
    code = cap.main([], env)
    out = json.loads(capsys.readouterr().out)
    on_disk = {p.relative_to(vault).as_posix() for p in (vault / "_ingest").rglob("*.md") if not p.name.startswith(".")}
    skipped = {s.get("path") for s in out["skipped"] if s.get("reason") == "already-fetched"}
    assert code == 0 and out["errors"] == []
    assert not (on_disk & skipped), out
    assert on_disk <= set(out["written"]), out


def test_us72_r2_capability_rerun_without_clearing_still_skips(vault, env, capsys):  # r1-6 control
    cap = _load("gilberto-capability-fetch", "cap_us72_r2c")
    src = vault / "anatomy/playbooks/intelligence/sources/core.md"
    src.parent.mkdir(parents=True)
    src.write_text(f'---\ntype: anatomy-sources\n---\n\n```yaml\n"{URL}":\n  type: rss\n```\n')
    assert cap.main([], env) == 0
    capsys.readouterr()
    code = cap.main([], env)
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["written"] == [] and len(list((vault / "_ingest").rglob("*.md"))) == 2


def test_us72_r2_capability_rerun_after_ingest_archived_writes_nothing(vault, env, capsys):  # r1-6 control
    cap = _load("gilberto-capability-fetch", "cap_us72_r2a")
    src = vault / "anatomy/playbooks/intelligence/sources/core.md"
    src.parent.mkdir(parents=True)
    src.write_text(f'---\ntype: anatomy-sources\n---\n\n```yaml\n"{URL}":\n  type: rss\n```\n')
    assert cap.main([], env) == 0
    for p in (vault / "_ingest" / "intelligence").glob("*.md"):
        p.unlink()
    assert (vault / "_ingest" / "intelligence" / ".fetch-rss").exists()
    capsys.readouterr()
    code = cap.main([], env)
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["written"] == [], out
    assert not list((vault / "_ingest").rglob("*.md"))
