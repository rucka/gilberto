import importlib.util
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(f"ingest_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


script = load("script")
activate = load("activate")

ARCHIVE = """import argparse, os, shutil, sys
p = argparse.ArgumentParser()
p.add_argument("--source"); p.add_argument("--pillar"); p.add_argument("--name")
a = p.parse_args()
if os.environ.get("STUB_FAIL"):
    print("boom", file=sys.stderr); sys.exit(3)
shutil.copy(a.source, os.path.join(os.environ["GILBERTO_ROOT"], a.pillar, a.name))
"""


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "vault"
    for d in ("me", "pulse", "projects", "intelligence", "journey", "_ingest"):
        (root / d).mkdir(parents=True)
    skills = tmp_path / "plugins" / "p" / "skills"
    skills.mkdir(parents=True)
    return {"GILBERTO_ROOT": str(root), "GILBERTO_SKILLS_DIR": str(tmp_path / "plugins"), "HOME": str(tmp_path / "home")}


@pytest.fixture
def stub_archive(env):
    def add(pillar):
        d = Path(env["GILBERTO_SKILLS_DIR"]) / "p" / "skills" / f"gilberto-capability-{pillar}-archive"
        d.mkdir(parents=True, exist_ok=True)
        (d / "script.py").write_text(ARCHIVE)

    return add


@pytest.fixture
def drop(env):
    def put(name, data=b"%PDF-1.4", age=60):
        p = Path(env["GILBERTO_ROOT"]) / "_ingest" / name
        p.write_bytes(data)
        t = time.time() - age
        os.utime(p, (t, t))
        return p

    return put


def run(env, capsys, *argv):
    capsys.readouterr()
    code = script.main(list(argv), env)
    return code, json.loads(capsys.readouterr().out)


def root(env):
    return Path(env["GILBERTO_ROOT"])


def test_ac1_archives_with_sidecar_and_removes_source(env, capsys, drop, stub_archive):
    stub_archive("intelligence")
    drop("paper.pdf")
    code, out = run(env, capsys, "apply", "--file=paper.pdf", "--pillar=intelligence", "--confidence=0.9")
    assert code == 0 and out["status"] == "archived"
    assert (root(env) / "intelligence" / "paper.pdf").read_bytes() == b"%PDF-1.4"
    side = json.loads((root(env) / "intelligence" / "paper.pdf.ingest.json").read_text())
    assert side["source"] == "_ingest/paper.pdf" and side["pillar"] == "intelligence" and side["confidence"] == 0.9
    assert not (root(env) / "_ingest" / "paper.pdf").exists()


@pytest.mark.parametrize("pillar", ["me", "pulse", "projects", "intelligence", "journey"])
def test_dispatch_target_per_pillar(env, capsys, drop, stub_archive, pillar):
    stub_archive(pillar)
    drop("a.md", b"x")
    _, out = run(env, capsys, "apply", "--file=a.md", "--pillar=" + pillar, "--confidence=0.8")
    assert out["status"] == "archived" and (root(env) / pillar / "a.md").exists()


def test_threshold_boundary_inclusive(env, capsys, drop, stub_archive):
    stub_archive("me")
    drop("a.pdf")
    _, out = run(env, capsys, "apply", "--file=a.pdf", "--pillar=me", "--confidence=0.5", "--threshold=0.5")
    assert out["status"] == "archived"


def test_missing_archive_capability_error_sidecar(env, capsys, drop):
    drop("a.pdf")
    _, out = run(env, capsys, "apply", "--file=a.pdf", "--pillar=me", "--confidence=0.9")
    assert out["status"] == "error" and out["code"] == "ARCHIVE_MISSING"
    assert (root(env) / "_ingest" / "a.pdf").exists()
    assert "gilberto-capability-me-archive" in (root(env) / "_ingest" / "a.pdf.error.md").read_text()


def test_archive_failure_keeps_file_with_error(env, capsys, drop, stub_archive, monkeypatch):
    stub_archive("me")
    drop("a.pdf")
    monkeypatch.setenv("STUB_FAIL", "1")
    _, out = run(env, capsys, "apply", "--file=a.pdf", "--pillar=me", "--confidence=0.9")
    assert out["code"] == "ARCHIVE_FAILED"
    assert (root(env) / "_ingest" / "a.pdf").exists() and "boom" in (root(env) / "_ingest" / "a.pdf.error.md").read_text()


@pytest.mark.parametrize("pillar", ["none", "unknown", "network"])
def test_unclassifiable_error_sidecar(env, capsys, drop, pillar):
    drop("a.pdf")
    _, out = run(env, capsys, "apply", "--file=a.pdf", "--pillar=" + pillar, "--confidence=0.9")
    assert out["code"] == "UNCLASSIFIABLE" and (root(env) / "_ingest" / "a.pdf.error.md").exists()


def test_unsupported_file_error_sidecar(env, capsys, drop, stub_archive):
    stub_archive("me")
    drop("a.exe")
    _, out = run(env, capsys, "apply", "--file=a.exe", "--pillar=me", "--confidence=0.9")
    assert out["code"] == "UNSUPPORTED" and (root(env) / "_ingest" / "a.exe").exists()


def test_collision_suffix_never_overwrites(env, capsys, drop, stub_archive):
    stub_archive("me")
    (root(env) / "me" / "a.pdf").write_bytes(b"old")
    (root(env) / "me" / "a-1.pdf").write_bytes(b"old1")
    drop("a.pdf", b"new")
    _, out = run(env, capsys, "apply", "--file=a.pdf", "--pillar=me", "--confidence=0.9")
    assert out["status"] == "archived" and out["archived"] == "me/a-2.pdf"
    assert (root(env) / "me" / "a.pdf").read_bytes() == b"old"
    assert (root(env) / "me" / "a-1.pdf").read_bytes() == b"old1"
    assert (root(env) / "me" / "a-2.pdf").read_bytes() == b"new"
    assert (root(env) / "me" / "a-2.pdf.ingest.json").exists()


def test_partial_write_skipped(env, capsys, drop, stub_archive):
    stub_archive("me")
    drop("a.pdf", age=0)
    _, scan = run(env, capsys, "scan")
    assert scan["files"] == []
    _, out = run(env, capsys, "apply", "--file=a.pdf", "--pillar=me", "--confidence=0.9")
    assert out["status"] == "skipped" and out["reason"] == "unstable"
    assert (root(env) / "_ingest" / "a.pdf").exists() and not (root(env) / "_ingest" / "a.pdf.error.md").exists()


def test_scan_lists_stable_only_skips_sidecars_hidden_and_errored(env, capsys, drop):
    drop("a.pdf")
    drop("b.md")
    drop(".hidden.md")
    drop("c.pdf.ingest.json")
    drop("d.pdf")
    drop("d.pdf.error.md")
    (root(env) / "_ingest" / "sub").mkdir()
    _, out = run(env, capsys, "scan")
    assert out["files"] == ["a.pdf", "b.md"]


def test_concurrent_run_is_noop(env, capsys, drop, stub_archive):
    import fcntl

    stub_archive("me")
    drop("a.pdf")
    with open(root(env) / "_ingest" / ".ingest.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        code, out = run(env, capsys, "apply", "--file=a.pdf", "--pillar=me", "--confidence=0.9")
        _, scan = run(env, capsys, "scan")
    assert code == 0 and out["status"] == "skipped" and out["reason"] == "locked"
    assert scan["status"] == "skipped" and scan["files"] == []
    assert (root(env) / "_ingest" / "a.pdf").exists() and not (root(env) / "me" / "a.pdf").exists()


@pytest.mark.parametrize("name", ["../x.pdf", "/etc/passwd", "sub/x.pdf"])
def test_paths_confined_to_ingest(env, capsys, name):
    code, out = run(env, capsys, "apply", f"--file={name}", "--pillar=me", "--confidence=0.9")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH"


def test_missing_file_errors(env, capsys):
    code, out = run(env, capsys, "apply", "--file=nope.pdf", "--pillar=me", "--confidence=0.9")
    assert code == 1 and out["errors"][0]["code"] == "NOT_FOUND"


# --- activation (fake launchctl) ---

LABEL = "com.foomakers.gilberto.ingest"


@pytest.fixture
def fake_launchctl(tmp_path, env, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "launchctl.log"
    state = tmp_path / "loaded"
    sh = bindir / "launchctl"
    sh.write_text(
        f'#!/bin/sh\necho "$@" >> {log}\n'
        f'case "$1" in print) [ -f {state} ] && exit 0 || exit 113;; bootstrap) touch {state}; exit 0;; esac\nexit 1\n'
    )
    sh.chmod(sh.stat().st_mode | stat.S_IXUSR)
    env["PATH"] = f"{bindir}{os.pathsep}/usr/bin{os.pathsep}/bin"
    agents = Path(env["HOME"]) / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    return SimpleLaunchctl(log, agents / f"{LABEL}.plist")


class SimpleLaunchctl:
    def __init__(self, log, plist):
        self.log, self.plist = log, plist

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []


def install_skill(env):
    (Path(env["GILBERTO_SKILLS_DIR"]) / "p" / "skills" / "gilberto-process-ingest").mkdir(parents=True)


def act(env, capsys):
    capsys.readouterr()
    code = activate.main([], env)
    return code, json.loads(capsys.readouterr().out)


def test_ac2_loads_job_when_skill_and_plist_present(env, capsys, fake_launchctl):
    install_skill(env)
    fake_launchctl.plist.write_text("<plist/>")
    code, out = act(env, capsys)
    assert code == 0 and out["status"] == "loaded"
    assert f"bootstrap gui/{os.getuid()} {fake_launchctl.plist}" in fake_launchctl.calls()


def test_activation_idempotent(env, capsys, fake_launchctl):
    install_skill(env)
    fake_launchctl.plist.write_text("<plist/>")
    act(env, capsys)
    code, out = act(env, capsys)
    assert code == 0 and out["status"] == "already-loaded"
    assert sum(c.startswith("bootstrap") for c in fake_launchctl.calls()) == 1


def test_ac3_skill_absent_stays_unloaded_no_error(env, capsys, fake_launchctl):
    fake_launchctl.plist.write_text("<plist/>")
    code, out = act(env, capsys)
    assert code == 0 and out["status"] == "skipped" and out["reason"] == "skill-not-installed"
    assert fake_launchctl.calls() == []


def test_plist_missing_noop(env, capsys, fake_launchctl):
    install_skill(env)
    code, out = act(env, capsys)
    assert code == 0 and out["reason"] == "plist-missing" and fake_launchctl.calls() == []


def test_bootstrap_failure_reported(env, capsys, fake_launchctl):
    install_skill(env)
    fake_launchctl.plist.write_text("<plist/>")
    sh = Path(env["PATH"].split(os.pathsep)[0]) / "launchctl"
    sh.write_text("#!/bin/sh\nexit 5\n")
    code, out = act(env, capsys)
    assert code == 1 and out["errors"][0]["code"] == "LAUNCHCTL_FAILED"


def test_non_darwin_skips(env, capsys, fake_launchctl, monkeypatch):
    install_skill(env)
    fake_launchctl.plist.write_text("<plist/>")
    monkeypatch.setattr(activate.sys, "platform", "linux")
    code, out = act(env, capsys)
    assert code == 0 and out["reason"] == "not-macos" and fake_launchctl.calls() == []


def test_cli_entrypoints_run_as_scripts(env, drop):
    drop("a.pdf", age=0)
    e = {**os.environ, **env}
    r = subprocess.run([sys.executable, str(HERE / "script.py"), "scan"], env=e, capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout)["files"] == []
    r = subprocess.run([sys.executable, str(HERE / "activate.py")], env=e, capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout)["status"] == "skipped"


def test_seed_plist_arg_resolves_via_dispatch_sh(env, tmp_path):
    seed = HERE.parents[3] / "packages" / "vault-bootstrap" / "seed"
    arg = __import__("re").search(r"dispatch\.sh</string>\s*<string>([^<]+)</string>", (seed / "launchd" / "ingest-watch.plist").read_text()).group(1)
    install_skill(env)
    bindir = tmp_path / "cbin"
    bindir.mkdir()
    claude = bindir / "claude"
    claude.write_text('#!/bin/sh\necho "ran $*"\n')
    claude.chmod(0o755)
    r = subprocess.run(["sh", str(seed / "hooks" / "dispatch.sh"), arg], capture_output=True, text=True,
                       env={"PATH": f"{bindir}:/usr/bin:/bin", "GILBERTO_SKILLS_DIR": env["GILBERTO_SKILLS_DIR"]})
    assert r.stdout.strip() == "ran -p /gilberto-process-ingest"
