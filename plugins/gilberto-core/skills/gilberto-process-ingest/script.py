#!/usr/bin/env python3
"""gilberto-process-ingest: filesystem side of `_ingest/` classification (LLM picks pillar+confidence in SKILL.md)."""
import argparse
import fcntl
import glob
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import atomic_write, result, vault_io  # noqa: E402
from _lib.result import MechanicError  # noqa: E402

PILLARS = ("me", "pulse", "projects", "intelligence", "journey")
SUPPORTED = {".pdf", ".md", ".txt", ".html", ".docx", ".png", ".jpg", ".jpeg"}
SIDECARS = (".ingest.json", ".error.md")
LOCK = ".ingest.lock"
RUN = ".ingest.run"


class Parser(result.ArgParser):
    pass


def _parse(argv):
    p = Parser(prog="gilberto-process-ingest")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    a = sub.add_parser("apply")
    a.add_argument("--file", required=True)
    a.add_argument("--pillar", required=True)
    a.add_argument("--confidence", type=float, required=True)
    a.add_argument("--threshold", type=float, default=0.7)
    for x in (s, a):
        x.add_argument("--min-age", type=float, default=5.0)
    return p.parse_args(argv)


def _stable(path, min_age):
    return time.time() - os.path.getmtime(path) >= min_age


def _lock(ingest):
    f = open(os.path.join(ingest, LOCK), "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True


def _claim_run(ingest):
    path = os.path.join(ingest, RUN)
    me = os.getppid()
    try:
        with open(path) as f:
            owner = int(f.read().strip())
    except (OSError, ValueError):
        owner = None
    if owner is not None and owner != me and _alive(owner):
        return False
    with open(path, "w") as f:
        f.write(str(me))
    return True


def _scan(ingest, min_age):
    out = []
    for n in sorted(os.listdir(ingest)):
        p = os.path.join(ingest, n)
        if n.startswith(".") or n.endswith(SIDECARS) or not os.path.isfile(p):
            continue
        if os.path.exists(p + ".error.md") or not _stable(p, min_age):
            continue
        out.append(n)
    return out


def _find_skill(env, name):
    base = env.get("GILBERTO_SKILLS_DIR") or os.path.join(env.get("HOME", os.path.expanduser("~")), ".claude", "plugins")
    hits = sorted(glob.glob(os.path.join(base, "**", "skills", name, "script.py"), recursive=True))
    return hits[0] if hits else None


def _unique(root, pillar, name):
    stem, ext = os.path.splitext(name)
    cand, i = name, 0
    while os.path.lexists(os.path.join(root, pillar, cand)) or os.path.lexists(os.path.join(root, pillar, cand + ".ingest.json")):
        i += 1
        cand = f"{stem}-{i}{ext}"
    return cand


def _error(ingest, name, code, detail):
    body = f"# Ingest error: {code}\n\n- file: {name}\n- detail: {detail}\n"
    atomic_write.atomic_write(os.path.join(ingest, name + ".error.md"), body)
    return {"status": "error", "code": code, "detail": detail, "file": name}


def _apply(a, root, ingest, env):
    name = a.file
    if os.path.basename(name) != name or name in ("", ".", ".."):
        raise MechanicError("INVALID_PATH", input=name)
    src = vault_io.resolve(root, f"_ingest/{name}")
    if os.path.dirname(src) != ingest:
        raise MechanicError("INVALID_PATH", input=name)
    if not os.path.isfile(src):
        raise MechanicError("NOT_FOUND", input=name)
    lock = _lock(ingest)
    if lock is None:
        return {"status": "skipped", "reason": "locked", "file": name}
    try:
        if not _stable(src, a.min_age):
            return {"status": "skipped", "reason": "unstable", "file": name}
        if os.path.splitext(name)[1].lower() not in SUPPORTED:
            return _error(ingest, name, "UNSUPPORTED", f"extension not in {sorted(SUPPORTED)}")
        if a.pillar not in PILLARS:
            return _error(ingest, name, "UNCLASSIFIABLE", f"pillar {a.pillar!r} not in {list(PILLARS)}")
        if a.confidence < a.threshold:
            return {"status": "kept", "reason": "below-threshold", "file": name, "confidence": a.confidence, "threshold": a.threshold}
        cap = f"gilberto-capability-{a.pillar}-archive"
        script = _find_skill(env, cap)
        if script is None:
            return _error(ingest, name, "ARCHIVE_MISSING", f"skill {cap} not installed")
        target = _unique(root, a.pillar, name)
        r = subprocess.run(
            [sys.executable, script, f"--source={src}", f"--pillar={a.pillar}", f"--name={target}"],
            capture_output=True, text=True, env={**os.environ, **env},
        )
        dest = os.path.join(root, a.pillar, target)
        if r.returncode != 0 or not os.path.isfile(dest):
            return _error(ingest, name, "ARCHIVE_FAILED", (r.stderr or f"exit {r.returncode}; {a.pillar}/{target} not written").strip())
        rel = f"{a.pillar}/{target}"
        side = {"source": f"_ingest/{name}", "pillar": a.pillar, "confidence": a.confidence, "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        atomic_write.atomic_write(dest + ".ingest.json", json.dumps(side) + "\n")
        os.unlink(src)
        stale = src + ".error.md"
        if os.path.exists(stale):
            os.unlink(stale)
        return {"status": "archived", "file": name, "archived": rel}
    finally:
        lock.close()


def main(argv=None, env=None):
    argv = sys.argv[1:] if argv is None else argv
    env = os.environ if env is None else env
    try:
        a = _parse(argv)
        root = vault_io.vault_root(env)
        ingest = vault_io.resolve(root, "_ingest")
        if not os.path.isdir(ingest):
            raise MechanicError("NOT_FOUND", input="_ingest")
        if a.cmd == "scan":
            lock = _lock(ingest)
            claimed = lock is not None and _claim_run(ingest)
            if lock is not None:
                lock.close()
            if claimed:
                out = {"status": "ok", "files": _scan(ingest, a.min_age)}
            else:
                out = {"status": "skipped", "reason": "locked", "files": []}
        else:
            out = _apply(a, root, ingest, env)
    except MechanicError as e:
        result.log(f"error: {e.code}")
        result.emit("error", errors=[e.as_dict()])
        return 1
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
