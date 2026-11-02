import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SUITE = HERE / "test_ingest.py"

LAUNCH = (
    "import sys; sys.platform = sys.argv[1]; import pytest; "
    "sys.exit(pytest.main(['-q', '-p', 'no:cacheprovider', *sys.argv[2:]]))"
)

ACTIVATION = (
    "test_ac2_loads_job_when_skill_and_plist_present",
    "test_activation_idempotent",
    "test_ac3_skill_absent_stays_unloaded_no_error",
    "test_plist_missing_noop",
    "test_bootstrap_failure_reported",
)


def nested(platform, names):
    ids = [f"{SUITE}::{n}" for n in names]
    return subprocess.run([sys.executable, "-c", LAUNCH, platform, *ids], capture_output=True, text=True)


@pytest.mark.parametrize("name", ACTIVATION)
def test_activation_test_passes_on_non_darwin_runner(name):
    r = nested("linux", [name])
    assert r.returncode == 0, r.stdout[-800:]


def test_activation_tests_pass_on_darwin_runner():
    r = nested("darwin", ACTIVATION)
    assert r.returncode == 0, r.stdout[-800:]


def test_non_darwin_skips_and_never_calls_launchctl(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("ci_platform_activate", HERE.parent / "activate.py")
    activate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(activate)
    bindir, log = tmp_path / "bin", tmp_path / "launchctl.log"
    bindir.mkdir()
    sh = bindir / "launchctl"
    sh.write_text(f'#!/bin/sh\necho "$@" >> {log}\nexit 0\n')
    sh.chmod(sh.stat().st_mode | stat.S_IXUSR)
    skills = tmp_path / "plugins" / "p" / "skills" / "gilberto-process-ingest"
    skills.mkdir(parents=True)
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    (agents / "com.foomakers.gilberto.ingest.plist").write_text("<plist/>")
    env = {"HOME": str(tmp_path / "home"), "GILBERTO_SKILLS_DIR": str(tmp_path / "plugins"), "PATH": f"{bindir}{os.pathsep}/usr/bin{os.pathsep}/bin"}
    monkeypatch.setattr(activate.sys, "platform", "linux")
    out = activate.activate(env)
    assert json.dumps(out, sort_keys=True) == json.dumps({"reason": "not-macos", "status": "skipped"}, sort_keys=True)
    assert not log.exists()


@pytest.mark.parametrize("platform", ("linux", "darwin"))
def test_suite_non_darwin_skips_passes_on_any_runner(platform):
    r = nested(platform, ["test_non_darwin_skips"])
    assert r.returncode == 0, r.stdout[-800:]
