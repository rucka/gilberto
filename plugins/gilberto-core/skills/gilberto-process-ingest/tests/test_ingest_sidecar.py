import importlib.util
import json
import os
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ingest_sidecar_script", HERE / "script.py")
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)

ARCHIVE = """import argparse, os, shutil
p = argparse.ArgumentParser()
p.add_argument("--source"); p.add_argument("--pillar"); p.add_argument("--name")
a = p.parse_args()
shutil.copy(a.source, os.path.join(os.environ["GILBERTO_ROOT"], a.pillar, a.name))
"""


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "vault"
    for d in ("me", "pulse", "projects", "intelligence", "journey", "_ingest", "anatomy"):
        (root / d).mkdir(parents=True)
    for p in ("me", "pulse"):
        d = tmp_path / "plugins" / "p" / "skills" / f"gilberto-capability-{p}-archive"
        d.mkdir(parents=True)
        (d / "script.py").write_text(ARCHIVE)
    return {"GILBERTO_ROOT": str(root), "GILBERTO_SKILLS_DIR": str(tmp_path / "plugins"), "HOME": str(tmp_path)}


def root(env):
    return Path(env["GILBERTO_ROOT"])


def drop(env, name="a.pdf", data=b"%PDF"):
    p = root(env) / "_ingest" / name
    p.write_bytes(data)
    t = time.time() - 60
    os.utime(p, (t, t))
    return p


def prefs(env, body):
    (root(env) / "anatomy" / "preferences.md").write_text(body)


def run(env, capsys, *argv):
    capsys.readouterr()
    code = script.main(list(argv), env)
    return code, json.loads(capsys.readouterr().out)


def keep(env, capsys, *extra):
    drop(env)
    return run(env, capsys, "apply", "--file=a.pdf", "--pillar=me", "--confidence=0.3", *extra)


def sidecar(env, name="a.pdf"):
    return root(env) / "_ingest" / (name + ".classification.json")


def test_ac1_kept_writes_sidecar(env, capsys):
    alts = json.dumps([{"pillar": "pulse", "confidence": 0.2}])
    code, out = keep(env, capsys, "--alternatives=" + alts)
    assert code == 0 and out["status"] == "kept"
    assert (root(env) / "_ingest" / "a.pdf").exists()
    s = json.loads(sidecar(env).read_text())
    assert s["proposal"] == "me" and s["confidence"] == 0.3 and s["threshold"] == 0.7
    assert s["alternatives"] == [{"pillar": "pulse", "confidence": 0.2}] and s["proposed_at"].endswith("Z")


def test_ac1_sidecar_rewritten_on_reclassification(env, capsys):
    keep(env, capsys)
    run(env, capsys, "apply", "--file=a.pdf", "--pillar=pulse", "--confidence=0.4")
    s = json.loads(sidecar(env).read_text())
    assert s["proposal"] == "pulse" and s["confidence"] == 0.4 and s["alternatives"] == []


def test_alternatives_invalid_rejected(env, capsys):
    drop(env)
    code, out = run(env, capsys, "apply", "--file=a.pdf", "--pillar=me", "--confidence=0.3", "--alternatives=[{")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_ARGS" and not sidecar(env).exists()


def test_ac2_threshold_from_preferences(env, capsys):
    prefs(env, "# P\n\n## Thresholds\n\nLimits.\n\ningest-confidence: 0.2\n\n## Cadences\n")
    drop(env)
    _, out = run(env, capsys, "apply", "--file=a.pdf", "--pillar=me", "--confidence=0.3")
    assert out["status"] == "archived"


def test_ac2_flag_overrides_preferences(env, capsys):
    prefs(env, "## Thresholds\ningest-confidence: 0.2\n")
    _, out = keep(env, capsys, "--threshold=0.9")
    assert out["status"] == "kept" and json.loads(sidecar(env).read_text())["threshold"] == 0.9


@pytest.mark.parametrize(
    "body",
    [
        "## Thresholds\ningest-confidence: abc\n",
        "## Thresholds\ningest-confidence: 1.5\n",
        "## Thresholds\ningest-confidence: nan\n",
        "## Thresholds\nother: 0.1\n",
        "## Cadences\ningest-confidence: 0.1\n",
        None,
    ],
)
def test_ac3_default_when_absent_or_invalid(env, capsys, body):
    if body is not None:
        prefs(env, body)
    code, out = keep(env, capsys)
    assert code == 0 and out["status"] == "kept" and json.loads(sidecar(env).read_text())["threshold"] == 0.7


def test_ac6_scan_excludes_pending_and_status_reports(env, capsys):
    keep(env, capsys)
    drop(env, "b.pdf")
    _, out = run(env, capsys, "scan")
    assert out["files"] == ["b.pdf"]
    _, st = run(env, capsys, "status")
    assert st["pending"] == [{"file": "a.pdf", "sidecar": "_ingest/a.pdf.classification.json"}]


def test_ac4_confirm_archives_and_cleans(env, capsys):
    keep(env, capsys)
    code, out = run(env, capsys, "confirm", "--file=a.pdf")
    assert code == 0 and out["status"] == "archived" and out["archived"] == "me/a.pdf"
    assert (root(env) / "me" / "a.pdf").read_bytes() == b"%PDF"
    side = json.loads((root(env) / "me" / "a.pdf.ingest.json").read_text())
    assert side["confidence"] == 1.0 and side["pillar"] == "me"
    assert not sidecar(env).exists() and not (root(env) / "_ingest" / "a.pdf").exists()


def test_ac4_confirm_pillar_override_and_current_file(env, capsys):
    keep(env, capsys)
    drop(env, data=b"changed")
    _, out = run(env, capsys, "confirm", "--file=a.pdf", "--pillar=pulse")
    assert out["archived"] == "pulse/a.pdf" and (root(env) / "pulse" / "a.pdf").read_bytes() == b"changed"
    assert json.loads((root(env) / "pulse" / "a.pdf.ingest.json").read_text())["pillar"] == "pulse"


def test_confirm_never_overwrites(env, capsys):
    keep(env, capsys)
    (root(env) / "me" / "a.pdf").write_bytes(b"old")
    _, out = run(env, capsys, "confirm", "--file=a.pdf")
    assert out["archived"] == "me/a-1.pdf" and (root(env) / "me" / "a.pdf").read_bytes() == b"old"


def test_confirm_invalid_pillar(env, capsys):
    keep(env, capsys)
    code, out = run(env, capsys, "confirm", "--file=a.pdf", "--pillar=nope")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_ARGS"
    assert sidecar(env).exists() and (root(env) / "_ingest" / "a.pdf").exists()


@pytest.mark.parametrize("bad", ["{", "[]", '{"proposal": "nope"}', '{"confidence": 1}'])
def test_confirm_malformed_sidecar(env, capsys, bad):
    drop(env)
    sidecar(env).write_text(bad)
    code, out = run(env, capsys, "confirm", "--file=a.pdf")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_SIDECAR"
    assert (root(env) / "_ingest" / "a.pdf").exists() and not (root(env) / "me" / "a.pdf").exists()


@pytest.mark.parametrize("cmd", ["confirm", "reject"])
def test_without_sidecar_not_found(env, capsys, cmd):
    drop(env)
    code, out = run(env, capsys, cmd, "--file=a.pdf")
    assert code == 1 and out["errors"][0]["code"] == "NOT_FOUND"


def test_confirm_locked_skipped(env, capsys):
    keep(env, capsys)
    lock = script._lock(str(root(env) / "_ingest"))
    _, out = run(env, capsys, "confirm", "--file=a.pdf")
    lock.close()
    assert out["status"] == "skipped" and out["reason"] == "locked" and sidecar(env).exists()


def test_confirm_path_traversal(env, capsys):
    code, out = run(env, capsys, "confirm", "--file=../x")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH"


def test_ac5_reject(env, capsys):
    keep(env, capsys)
    code, out = run(env, capsys, "reject", "--file=a.pdf")
    assert code == 0 and out["status"] == "rejected"
    assert not sidecar(env).exists() and (root(env) / "_ingest" / "a.pdf").exists()
    assert "REJECTED" in (root(env) / "_ingest" / "a.pdf.error.md").read_text()
    _, scan = run(env, capsys, "scan")
    assert scan["files"] == []
    _, st = run(env, capsys, "status")
    assert st["pending"] == []
