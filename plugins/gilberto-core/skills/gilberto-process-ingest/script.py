#!/usr/bin/env python3
"""gilberto-process-ingest: filesystem side of `_ingest/` classification (LLM picks pillar+confidence in SKILL.md)."""
import argparse
import fcntl
import glob
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import atomic_write, result, vault_io  # noqa: E402
from _lib.result import MechanicError  # noqa: E402

PILLARS = ("me", "pulse", "projects", "intelligence", "journey")
SUPPORTED = {".pdf", ".md", ".txt", ".html", ".docx", ".png", ".jpg", ".jpeg"}
SIDECARS = (".ingest.json", ".error.md", ".classification.json")
CLASSIFICATION = ".classification.json"
DEFAULT_THRESHOLD = 0.7
_N = r"(\d+(?:\.\d+)?|\.\d+)"
THRESHOLD_LINE = re.compile(rf"^(?:[-*][ \t]+)?(?:`ingest-confidence:[ \t]*{_N}`(?:[ \t].*)?|ingest-confidence:[ \t]*{_N}[ \t]*)$")
LOCK = ".ingest.lock"
RUN = ".ingest.run"


class Parser(result.ArgParser):
    pass


def _unit(v):
    f = float(v)
    if not 0.0 <= f <= 1.0:  # rejects nan/inf too
        raise argparse.ArgumentTypeError(f"{v!r} not in [0,1]")
    return f


def _alternatives(v):
    try:
        alts = json.loads(v)
        ok = isinstance(alts, list) and all(isinstance(x, dict) and x.get("pillar") in PILLARS and isinstance(x.get("confidence"), (int, float)) for x in alts)
    except ValueError:
        ok = False
    if not ok:
        raise argparse.ArgumentTypeError(f"{v!r} not a JSON list of {{pillar,confidence}}")
    return [{"pillar": x["pillar"], "confidence": x["confidence"]} for x in alts]


def _threshold(root, flag):
    if flag is not None:
        return flag
    try:
        with open(os.path.join(root, "anatomy", "preferences.md")) as f:
            lines = f.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return DEFAULT_THRESHOLD
    in_section = False
    for line in lines:
        if line.startswith("## "):
            in_section = line.strip() == "## Thresholds"
        elif in_section:
            m = THRESHOLD_LINE.match(line.strip())
            v = m and float(m.group(1) or m.group(2))
            if m and 0.0 <= v <= 1.0:
                return v
    return DEFAULT_THRESHOLD


def _parse(argv):
    p = Parser(prog="gilberto-process-ingest")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    a = sub.add_parser("apply")
    a.add_argument("--file", required=True)
    a.add_argument("--pillar", required=True)
    a.add_argument("--confidence", type=_unit, required=True)
    a.add_argument("--threshold", type=_unit, default=None)
    a.add_argument("--alternatives", type=_alternatives, default=[])
    sub.add_parser("status")
    c = sub.add_parser("confirm")
    r = sub.add_parser("reject")
    for x in (c, r):
        x.add_argument("--file", required=True)
    c.add_argument("--pillar", choices=PILLARS)
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
        if os.path.exists(p + ".error.md") or os.path.exists(p + CLASSIFICATION) or not _stable(p, min_age):
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


def _status(ingest):
    return [
        {"file": n[: -len(CLASSIFICATION)], "sidecar": f"_ingest/{n}"}
        for n in sorted(os.listdir(ingest))
        if n.endswith(CLASSIFICATION) and not n.startswith(".") and os.path.isfile(os.path.join(ingest, n[: -len(CLASSIFICATION)]))
    ]


def _source(root, ingest, name):
    if os.path.basename(name) != name or name in ("", ".", ".."):
        raise MechanicError("INVALID_PATH", input=name)
    src = vault_io.resolve(root, f"_ingest/{name}")
    if os.path.dirname(src) != ingest:
        raise MechanicError("INVALID_PATH", input=name)
    if not os.path.isfile(src):
        raise MechanicError("NOT_FOUND", input=name)
    return src


def _archive(root, ingest, env, name, src, pillar, confidence):
    cap = f"gilberto-capability-{pillar}-archive"
    script = _find_skill(env, cap)
    if script is None:
        return _error(ingest, name, "ARCHIVE_MISSING", f"skill {cap} not installed")
    target = _unique(root, pillar, name)
    r = subprocess.run(
        [sys.executable, script, f"--source={src}", f"--pillar={pillar}", f"--name={target}"],
        capture_output=True, text=True, env={**os.environ, **env},
    )
    dest = os.path.join(root, pillar, target)
    if r.returncode != 0 or not os.path.isfile(dest):
        return _error(ingest, name, "ARCHIVE_FAILED", (r.stderr or f"exit {r.returncode}; {pillar}/{target} not written").strip())
    rel = f"{pillar}/{target}"
    side = {"source": f"_ingest/{name}", "pillar": pillar, "confidence": confidence, "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    atomic_write.atomic_write(dest + ".ingest.json", json.dumps(side) + "\n")
    os.unlink(src)
    for ext in (".error.md", CLASSIFICATION):
        if os.path.exists(src + ext):
            os.unlink(src + ext)
    return {"status": "archived", "file": name, "archived": rel}


def _confirm(a, root, ingest, env):
    src = _source(root, ingest, a.file)
    side = src + CLASSIFICATION
    if not os.path.isfile(side):
        raise MechanicError("NOT_FOUND", input=a.file + CLASSIFICATION)
    try:
        with open(side) as f:
            proposal = json.load(f)["proposal"]
    except (OSError, ValueError, KeyError, TypeError):
        proposal = None
    if proposal not in PILLARS:
        raise MechanicError("INVALID_SIDECAR", input=a.file + CLASSIFICATION)
    lock = _lock(ingest)
    if lock is None:
        return {"status": "skipped", "reason": "locked", "file": a.file}
    try:
        return _archive(root, ingest, env, a.file, src, a.pillar or proposal, 1.0)
    finally:
        lock.close()


def _reject(a, root, ingest):
    src = _source(root, ingest, a.file)
    side = src + CLASSIFICATION
    if not os.path.isfile(side):
        raise MechanicError("NOT_FOUND", input=a.file + CLASSIFICATION)
    lock = _lock(ingest)
    if lock is None:
        return {"status": "skipped", "reason": "locked", "file": a.file}
    try:
        _error(ingest, a.file, "REJECTED", "classification rejected by user")
        os.unlink(side)
        return {"status": "rejected", "file": a.file}
    finally:
        lock.close()


def _apply(a, root, ingest, env):
    name = a.file
    src = _source(root, ingest, name)
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
        threshold = _threshold(root, a.threshold)
        if a.confidence < threshold:
            side = {"proposal": a.pillar, "confidence": a.confidence, "threshold": threshold, "alternatives": a.alternatives, "proposed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            atomic_write.atomic_write(src + CLASSIFICATION, json.dumps(side) + "\n")
            return {"status": "kept", "reason": "below-threshold", "file": name, "confidence": a.confidence, "threshold": threshold}
        return _archive(root, ingest, env, name, src, a.pillar, a.confidence)
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
        elif a.cmd == "status":
            out = {"status": "ok", "pending": _status(ingest)}
        elif a.cmd == "confirm":
            out = _confirm(a, root, ingest, env)
        elif a.cmd == "reject":
            out = _reject(a, root, ingest)
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
