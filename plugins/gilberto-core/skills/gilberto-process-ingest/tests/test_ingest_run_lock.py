import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ingest_run_lock_script", HERE / "script.py")
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
    for d in ("me", "pulse", "projects", "intelligence", "journey", "_ingest"):
        (root / d).mkdir(parents=True)
    skill = tmp_path / "plugins" / "p" / "skills" / "gilberto-capability-me-archive"
    skill.mkdir(parents=True)
    (skill / "script.py").write_text(ARCHIVE)
    f = root / "_ingest" / "a.pdf"
    f.write_bytes(b"%PDF-1.4")
    t = time.time() - 60
    os.utime(f, (t, t))
    return {"GILBERTO_ROOT": str(root), "GILBERTO_SKILLS_DIR": str(tmp_path / "plugins"), "HOME": str(tmp_path / "home")}


def run(env, capsys, *argv):
    capsys.readouterr()
    code = script.main(list(argv), env)
    return code, json.loads(capsys.readouterr().out)


def other_process_scan(env):
    r = subprocess.run(
        [sys.executable, str(HERE / "script.py"), "scan"],
        capture_output=True, text=True, env={**os.environ, **env}, timeout=30,
    )
    return r.returncode, json.loads(r.stdout)


def test_second_scan_during_active_run_is_noop(env, capsys):
    code, first = run(env, capsys, "scan")
    assert code == 0 and first == {"status": "ok", "files": ["a.pdf"]}
    code, second = other_process_scan(env)
    assert code == 0 and second == {"status": "skipped", "reason": "locked", "files": []}


def test_run_own_apply_proceeds_after_its_scan(env, capsys):
    run(env, capsys, "scan")
    code, out = run(env, capsys, "apply", "--file=a.pdf", "--pillar=me", "--confidence=0.9")
    assert code == 0 and out["status"] == "archived"
    assert (Path(env["GILBERTO_ROOT"]) / "me" / "a.pdf").exists()


def test_first_scan_without_active_run_lists_files(env, capsys):
    code, out = run(env, capsys, "scan")
    assert code == 0 and out == {"status": "ok", "files": ["a.pdf"]}


RUN_SCAN = """import subprocess, sys, time
s = sys.argv[1]
subprocess.run([sys.executable, s, "scan"], check=True, capture_output=True)
print("scanned", flush=True)
if sys.argv[2] == "apply":
    subprocess.run([sys.executable, s, "apply", "--file=a.pdf", "--pillar=me", "--confidence=0.9"], check=True, capture_output=True)
else:
    time.sleep(60)
"""


def start_run(env, mode):
    p = subprocess.Popen(
        [sys.executable, "-c", RUN_SCAN, str(HERE / "script.py"), mode],
        stdout=subprocess.PIPE, text=True, env={**os.environ, **env},
    )
    assert p.stdout.readline().strip() == "scanned"
    return p


def add_second_file(env):
    f = Path(env["GILBERTO_ROOT"]) / "_ingest" / "b.pdf"
    f.write_bytes(b"%PDF-1.4")
    t = time.time() - 60
    os.utime(f, (t, t))


def test_scan_after_run_owner_killed_lists_files(env):
    p = start_run(env, "hold")
    p.kill()
    p.wait(timeout=30)
    code, out = other_process_scan(env)
    assert code == 0 and out == {"status": "ok", "files": ["a.pdf"]}


def test_scan_after_run_ended_lists_new_files(env):
    p = start_run(env, "apply")
    assert p.wait(timeout=30) == 0
    add_second_file(env)
    code, out = other_process_scan(env)
    assert code == 0 and out == {"status": "ok", "files": ["b.pdf"]}


def test_scan_skipped_while_run_process_alive_after_its_scan_exited(env):
    p = start_run(env, "hold")
    try:
        code, out = other_process_scan(env)
    finally:
        p.kill()
        p.wait(timeout=30)
    assert code == 0 and out == {"status": "skipped", "reason": "locked", "files": []}
