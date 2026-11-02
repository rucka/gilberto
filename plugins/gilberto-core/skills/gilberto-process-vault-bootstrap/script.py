#!/usr/bin/env python3
"""Path A entry shim: detect gilberto CLI, spawn `gilberto install --non-interactive`. No filesystem writes."""
import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys

REQUIRES = ">=0.1.0 <2"
DOCS_URL = "https://github.com/rucka/gilberto/blob/main/apps/website/content/docs/getting-started/install.mdx"
SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")
NET_ERR = re.compile(r"ENOTFOUND|ECONNREFUSED|ETIMEDOUT|EAI_AGAIN|ECONNRESET|^npm (?:error|ERR!) network", re.I | re.M)
MESSAGES = {
    1: "target path is a file, not a directory",
    2: None,
    13: "target path is not writable",
    28: "disk full",
    64: "bad or missing input",
    65: "invalid .claude/settings.json or launchd plist",
    70: "vault-bootstrap content package missing",
    130: "install aborted",
}


def parse_version(text):
    m = SEMVER.search(text or "")
    return tuple(int(x) for x in m.groups()) if m else None


def in_range(v):
    return v is not None and (0, 1, 0) <= v < (2, 0, 0)


def global_path(env):
    """PATH without project-local node_modules/.bin entries."""
    parts = [p for p in env.get("PATH", "").split(os.pathsep) if p and "node_modules/.bin" not in p.replace("\\", "/")]
    return os.pathsep.join(parts)


def run(argv, **kw):
    return subprocess.run(argv, capture_output=True, text=True, **kw)


def detect(env):
    """-> {'argv': [...], 'version': tuple|None, 'source': which|npm-global|npx}"""
    exe = shutil.which("gilberto", path=global_path(env))
    if exe:
        return {"argv": [exe], "version": parse_version(run([exe, "--version"], env=env).stdout), "source": "which"}
    try:
        r = run(["npm", "ls", "-g", "gilberto", "--depth=0", "--json"], env=env)
        ver = json.loads(r.stdout or "{}").get("dependencies", {}).get("gilberto", {}).get("version")
        if ver:
            prefix = run(["npm", "prefix", "-g"], env=env).stdout.strip()
            return {"argv": [os.path.join(prefix, "bin", "gilberto")], "version": parse_version(ver), "source": "npm-global"}
    except (OSError, ValueError):
        pass
    return {"argv": ["npx", "-y", "gilberto@latest"], "version": None, "source": "npx"}


def build_flags(a, platform):
    flags = ["install"]
    if a.target_path:
        flags.append(a.target_path)
    flags += ["--non-interactive", "-v"]
    if a.seed_topics:
        flags.append(f"--seed-topics={a.seed_topics}")
    if a.disable_hooks:
        flags.append("--no-hooks")
    notes = []
    if a.disable_launchd or platform != "darwin":
        flags.append("--no-launchd")
        if not a.disable_launchd:
            notes.append("auto-injected --no-launchd (non-macOS host)")
    return flags, notes


def summarize(out, a, notes):
    lines = out.splitlines()
    m = re.search(r'target="([^"]*)"', out)
    pillars = {"me", "pulse", "projects", "intelligence", "journey", "network"}
    n_pillars = sum(1 for l in lines if re.fullmatch(r'wrote dir="(%s)"' % "|".join(pillars), l))
    seeds = sum(1 for l in lines if l.startswith('wrote file="anatomy/'))
    hooks = "merged" if "merged-keys=" in out else "skipped"
    ld = re.search(r"step=launchd decision=(\w+)", out)
    return [
        f"vault: {a.target_path or (m.group(1) if m else 'default target')}",
        f"pillars: {n_pillars}",
        f"anatomy seeds: {seeds}",
        f"hooks: {hooks}",
        f"launchd: {ld.group(1) if ld else 'unknown'}",
        *notes,
        "next session: open the vault path above",
    ]


def spawn(argv, env):
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    old = signal.signal(signal.SIGTERM, lambda *_: (p.terminate(), None))
    try:
        out, err = p.communicate()
    finally:
        signal.signal(signal.SIGTERM, old)
    return p.returncode, out, err


def choose(a, msg):
    if a.confirm:
        return a.confirm
    print(msg, file=sys.stderr)
    if sys.stdin.isatty():
        return input("choose [upgrade|npx]: ").strip()
    return None


def main(argv, env=None, platform=None):
    env = dict(os.environ if env is None else env)
    platform = platform or sys.platform
    p = argparse.ArgumentParser(prog="gilberto-process-vault-bootstrap")
    p.add_argument("--target-path")
    p.add_argument("--seed-topics")
    p.add_argument("--enable-plugins")
    p.add_argument("--disable-hooks", action="store_true")
    p.add_argument("--disable-launchd", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--confirm", choices=["upgrade", "npx"])
    a = p.parse_args(argv)

    if a.verbose:
        for d in env.get("PATH", "").split(os.pathsep):
            if d and "node_modules/.bin" in d.replace("\\", "/") and shutil.which("gilberto", path=d):
                print(f"ignored local gilberto at {d}", file=sys.stderr)

    cli = detect(env)
    if cli["source"] != "npx" and not in_range(cli["version"]):
        got = ".".join(map(str, cli["version"])) if cli["version"] else "unknown"
        rel = "below" if cli["version"] and cli["version"] < (0, 1, 0) else "outside"
        c = choose(a, f"installed gilberto version {got} is {rel} required {REQUIRES}; upgrade with `npm i -g gilberto@latest` or rerun via `npx gilberto@latest`")
        if c == "upgrade":
            r = run(["npm", "i", "-g", "gilberto@latest"], env=env)
            if r.returncode:
                print(r.stderr, file=sys.stderr)
                return r.returncode
            cli = detect(env)
            if cli["source"] == "npx" or not in_range(cli["version"]):
                got = ".".join(map(str, cli["version"])) if cli["version"] else "unknown"
                print(f"after upgrade gilberto version {got} is still outside required {REQUIRES}", file=sys.stderr)
                return 64
        elif c == "npx":
            cli = {"argv": ["npx", "-y", "gilberto@latest"], "version": None, "source": "npx"}
        else:
            print("re-run with --confirm=upgrade or --confirm=npx", file=sys.stderr)
            return 64

    flags, notes = build_flags(a, platform)
    code, out, err = spawn(cli["argv"] + flags, env)
    if code == 0:
        trace = out + err
        print("\n".join(summarize(trace, a, notes)))
        if a.verbose:
            print(trace)
        return 0
    if cli["source"] == "npx" and NET_ERR.search(err):
        print(f"npm registry unreachable; install gilberto manually via the steps at {DOCS_URL} and re-run /gilberto-process-vault-bootstrap", file=sys.stderr)
        return 1
    if code == 2:
        print(err, file=sys.stderr, end="")
    elif code in MESSAGES:
        print(f"{MESSAGES[code]} (exit {code})\n{err}", file=sys.stderr)
    else:
        print(f"unexpected CLI failure (exit {code})\n{err}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
