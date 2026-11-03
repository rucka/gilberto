import importlib.util
import json
from pathlib import Path

import pytest

from rss_helpers import URL, Resp, fixture, http_error

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
    ing = _load("gilberto-process-ingest", "ingest_us72")
    capsys.readouterr()
    code = ing.main(list(argv), env)
    return code, json.loads(capsys.readouterr().out)


def _scan(env, capsys):
    code, out = _ingest(env, capsys, "scan", "--min-age=0")
    assert code == 0 and out["status"] == "ok"
    return out["files"]


def _md_under_ingest(vault):
    return sorted(p for p in (vault / "_ingest").rglob("*.md") if not p.name.startswith("."))


@pytest.mark.parametrize("kind_", ["rss", "atom"])
def test_us72_r1_dispatch_real_utility_accepted(vault, env, kind_):  # r0-1
    cap = _load("gilberto-capability-fetch", "cap_us72")
    kind, items = cap.dispatch(str(vault), {"type": kind_, "url": URL}, env)
    assert kind == "items" and sorted(i["id"] for i in items) == ["g-1", "g-2"]


def test_us72_r1_capability_run_items_reach_ingest_scan_once(vault, env, capsys):  # r0-1 + r0-2 interaction
    cap = _load("gilberto-capability-fetch", "cap_us72_run")
    src = vault / "anatomy/playbooks/intelligence/sources/core.md"
    src.parent.mkdir(parents=True)
    src.write_text(f'---\ntype: anatomy-sources\n---\n\n```yaml\n"{URL}":\n  type: rss\n```\n')
    capsys.readouterr()
    code = cap.main([], env)
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["errors"] == [] and len(out["written"]) == 2
    assert len(_md_under_ingest(vault)) == 2
    files = _scan(env, capsys)
    assert len(files) == 2 and all((vault / "_ingest" / f).is_file() for f in files)


def test_us72_r1_capability_run_is_idempotent(vault, env, capsys):  # r0-1
    cap = _load("gilberto-capability-fetch", "cap_us72_idem")
    src = vault / "anatomy/playbooks/intelligence/sources/core.md"
    src.parent.mkdir(parents=True)
    src.write_text(f'---\ntype: anatomy-sources\n---\n\n```yaml\n"{URL}":\n  type: rss\n```\n')
    assert cap.main([], env) == 0
    before = {p: p.read_bytes() for p in _md_under_ingest(vault)}
    capsys.readouterr()
    code = cap.main([], env)
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["errors"] == [] and out["written"] == []
    assert {p: p.read_bytes() for p in _md_under_ingest(vault)} == before and len(before) == 2


def _utility_env(run, root, capsys):
    code, out, _ = run(f"--url={URL}")
    assert code == 0 and len(out["items"]) == 2
    env = {"GILBERTO_ROOT": str(root), "GILBERTO_SKILLS_DIR": str(root / "plugins"), "HOME": str(root / "home")}
    arch = root / "plugins" / "p" / "skills" / "gilberto-capability-intelligence-archive"
    arch.mkdir(parents=True)
    (arch / "script.py").write_text(ARCHIVE)
    (root / "intelligence").mkdir(exist_ok=True)
    files = _scan(env, capsys)
    assert len(files) == 2
    return env, files


def _assert_archived(root, res, listed):
    base = Path(listed).name
    assert res["archived"] == f"intelligence/{base}", res
    assert (root / "intelligence" / base).is_file() and (root / "intelligence" / f"{base}.ingest.json").is_file()
    assert not (root / "intelligence" / "intelligence").exists()
    assert not [p for p in (root / "_ingest").rglob("*") if p.name.startswith(base)]


def _apply_low(env, capsys, listed):
    code, res = _ingest(env, capsys, "apply", f"--file={listed}", "--pillar=intelligence", "--confidence=0.1", "--min-age=0")
    assert code == 0 and res["status"] == "kept", res
    code, st = _ingest(env, capsys, "status")
    assert code == 0 and listed in [e["file"] for e in st["pending"]], st
    assert all((root_of(env) / e["sidecar"]).is_file() for e in st["pending"])


def root_of(env):
    return Path(env["GILBERTO_ROOT"])


def test_us72_r1_utility_output_listed_by_scan_and_applicable(run, root, capsys):  # r0-2
    env, files = _utility_env(run, root, capsys)
    for f in files:
        code, res = _ingest(env, capsys, "apply", f"--file={f}", "--pillar=intelligence", "--confidence=0.9", "--min-age=0")
        assert code == 0 and res["status"] == "archived", res
        _assert_archived(root, res, f)


def test_us72_r1_utility_low_confidence_status_then_confirm(run, root, capsys):  # r0-2 status/confirm
    env, files = _utility_env(run, root, capsys)
    _apply_low(env, capsys, files[0])
    code, res = _ingest(env, capsys, "confirm", f"--file={files[0]}")
    assert code == 0 and res["status"] == "archived", res
    _assert_archived(root, res, files[0])
    assert files[0] not in _scan(env, capsys)


def test_us72_r1_utility_low_confidence_status_then_reject(run, root, capsys):  # r0-2 status/reject
    env, files = _utility_env(run, root, capsys)
    _apply_low(env, capsys, files[1])
    code, res = _ingest(env, capsys, "reject", f"--file={files[1]}")
    assert code == 0 and res["status"] == "rejected", res
    src = root / "_ingest" / files[1]
    assert src.is_file() and Path(f"{src}.error.md").is_file() and not Path(f"{src}.classification.json").exists()
    assert files[1] not in _scan(env, capsys) and files[1] not in [e["file"] for e in _ingest(env, capsys, "status")[1]["pending"]]


def test_us72_r1_second_run_invalid_profile_rejected(run, root):  # r0-3
    assert run(f"--url={URL}")[0] == 0
    code, out, _ = run(f"--url={URL}", "--profile=nope")
    assert code == 1 and out["errors"][0]["code"] == "provider"


def test_us72_r1_second_run_valid_profile_still_empty(run, root):  # r0-3 control
    assert run(f"--url={URL}")[0] == 0
    code, out, _ = run(f"--url={URL}", "--profile=rss:default")
    assert code == 0 and out["items"] == []


def test_us72_r1_invalid_profile_on_empty_feed_rejected(run, root, serve):  # r0-3 boundary
    serve(Resp(fixture("feed.xml").replace(b"<item>", b"<x>").replace(b"</item>", b"</x>")))
    code, out, _ = run(f"--url={URL}", "--profile=nope")
    assert code == 1 and out["errors"][0]["code"] == "provider"


@pytest.mark.parametrize("profile", ["", "rss:", ":x", "a:b:c"])
def test_us72_r1_malformed_profile_rejected_on_rerun(run, root, profile):  # r0-3 malformed
    assert run(f"--url={URL}")[0] == 0
    code, out, _ = run(f"--url={URL}", f"--profile={profile}")
    assert code == 1 and out["errors"][0]["code"] == "provider"


def test_us72_r1_empty_profile_rejected_on_fresh_feed(run, root):  # r0-3 empty fresh
    code, out, _ = run(f"--url={URL}", "--profile=")
    assert code == 1 and out["errors"][0]["code"] == "provider"
    assert not list(root.rglob("*.md"))


def test_us72_r1_invalid_profile_precedes_fetch(run, root, serve):  # r0-3 ordering
    calls = serve(http_error(404))
    code, out, _ = run(f"--url={URL}", "--profile=nope")
    assert code == 1 and out["errors"][0]["code"] == "provider" and calls == []


@pytest.mark.parametrize("name", ["intelligence/../x.md", "intelligence/sub/x.md", "sub/x.pdf", "../x.pdf"])
def test_us72_r1_apply_rejects_traversal_and_nesting(vault, env, capsys, name):  # r0-2 negative
    (vault / "_ingest" / "intelligence" / "sub").mkdir(parents=True)
    (vault / "_ingest" / "intelligence" / "sub" / "x.md").write_text("x")
    (vault / "_ingest" / "intelligence" / "x.md").write_text("x")
    (vault / "x.md").write_text("x")
    code, res = _ingest(env, capsys, "apply", f"--file={name}", "--pillar=intelligence", "--confidence=0.9", "--min-age=0")
    assert code == 1 and res["errors"][0]["code"] == "INVALID_PATH", res
