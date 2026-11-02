#!/usr/bin/env python3
"""Idempotent first-run activation: load the ingest launchd job iff gilberto-process-ingest is installed."""
import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import result  # noqa: E402
from _lib.result import MechanicError  # noqa: E402

LABEL = "com.foomakers.gilberto.ingest"
SKILL = "gilberto-process-ingest"


def _installed(env):
    base = env.get("GILBERTO_SKILLS_DIR") or os.path.join(env.get("HOME", os.path.expanduser("~")), ".claude", "plugins")
    return bool(glob.glob(os.path.join(base, "**", "skills", SKILL), recursive=True))


def _launchctl(env, *args):
    return subprocess.run(["launchctl", *args], capture_output=True, text=True, env={**os.environ, **env})


def activate(env):
    if sys.platform != "darwin":
        return {"status": "skipped", "reason": "not-macos"}
    if not _installed(env):
        return {"status": "skipped", "reason": "skill-not-installed"}
    plist = os.path.join(env.get("HOME", os.path.expanduser("~")), "Library", "LaunchAgents", f"{LABEL}.plist")
    if not os.path.isfile(plist):
        return {"status": "skipped", "reason": "plist-missing"}
    domain = f"gui/{os.getuid()}"
    if _launchctl(env, "print", f"{domain}/{LABEL}").returncode == 0:
        return {"status": "already-loaded"}
    r = _launchctl(env, "bootstrap", domain, plist)
    if r.returncode != 0:
        raise MechanicError("LAUNCHCTL_FAILED", exit=r.returncode, stderr=r.stderr.strip())
    return {"status": "loaded"}


def main(argv=None, env=None):
    env = os.environ if env is None else env
    try:
        out = activate(env)
    except MechanicError as e:
        result.log(f"error: {e.code}")
        result.emit("error", errors=[e.as_dict()])
        return 1
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
