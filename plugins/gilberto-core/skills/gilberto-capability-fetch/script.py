import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import frontmatter, vault_io  # noqa: E402
from _lib.result import MechanicError  # noqa: E402

PLAYBOOKS = "anatomy/playbooks"
SKILLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTES = {"rss": "utility-fetch-rss", "atom": "utility-fetch-rss", "http": "utility-download-html"}
FALLBACKS = ("mcp", "none")
TIMEOUT = 120
_FENCE = re.compile(r"^```ya?ml[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)
_TOP = re.compile(r'^(?:"([^"\n]+)"|(https?://\S+?)):[ \t]*$')
_KV = re.compile(r"^[ \t]+([a-z_][a-z0-9_-]*):[ \t]*(.*?)[ \t]*$")


def _scalar(v):
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"" else v


def _entries(text):
    """-> [(url|None, fields|None)]; fields None = malformed."""
    out = []
    for m in _FENCE.finditer(text):
        cur = None
        for line in m.group(1).splitlines():
            if not line.strip():
                continue
            top = _TOP.match(line)
            kv = _KV.match(line)
            if top:
                cur = [top.group(1) or top.group(2), {}]
                out.append(cur)
            elif kv and cur and cur[1] is not None:
                cur[1][kv.group(1)] = _scalar(kv.group(2))
            elif cur and cur[1] is not None:
                cur[1] = None
            elif not cur:
                cur = [None, None]
                out.append(cur)
    return [tuple(e) for e in out]


def load_sources(root, pillar=None, source=None):
    """-> (entries, errors) from anatomy/playbooks/*/sources/*.md; a malformed entry is an error, the rest load."""
    entries, errors = [], []
    base = vault_io.resolve(root, PLAYBOOKS)
    if not os.path.isdir(base):
        return entries, errors
    for p in sorted(os.listdir(base)):
        if pillar and p != pillar:
            continue
        folder = os.path.join(base, p, "sources")
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".md"):
                continue
            contributor = name[:-3]
            rel = f"{PLAYBOOKS}/{p}/sources/{name}"
            with open(vault_io.resolve(root, rel), encoding="utf-8") as f:
                text = f.read()
            for url, fields in _entries(text):
                if source and source not in (contributor, url):
                    continue
                if fields is None or not (fields.get("type") or fields.get("provider")):
                    errors.append({"code": "MALFORMED_ENTRY", "source": rel, "url": url})
                    continue
                entries.append({"pillar": p, "contributor": contributor, "url": url, "file": rel, **fields})
    return entries, errors


def resolve_profile(root, entry):
    """Stub for the #60 resolver (explicit > folder note > global default > profile-unresolved): no profile."""
    return None


def _utility_dirs(env):
    return [SKILLS] + [d for d in env.get("GILBERTO_UTILITY_PATH", "").split(os.pathsep) if d]


def _script(name, env):
    for d in _utility_dirs(env):
        path = os.path.join(d, name, "script.py")
        if os.path.isfile(path):
            return path


def _fallback(entry, integration):
    value = entry.get("fallback")
    if value is None and integration:
        with open(integration, encoding="utf-8") as f:
            value = frontmatter.parse(f.read())[0].get("fallback")
    value = value or "none"
    if value not in FALLBACKS:
        raise MechanicError("INVALID_FALLBACK", fallback=value, allowed=list(FALLBACKS))
    return value


def _run_utility(name, path, root, entry, env):
    profile = entry.get("profile") or resolve_profile(root, entry)
    argv = [sys.executable, path, f"--url={entry['url']}"] + ([f"--profile={profile}"] if profile else [])
    bad = lambda **x: MechanicError("UTILITY_ERROR", utility=name, **x)
    try:
        p = subprocess.run(argv, env={**os.environ, **env, "GILBERTO_ROOT": root}, capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise bad(error=str(e))
    try:
        out = json.loads(p.stdout)
    except ValueError:
        raise bad(exit=p.returncode, stderr=p.stderr.strip()[:500], reason="stdout is not JSON")
    if p.returncode:
        errs = out.get("errors") if isinstance(out, dict) else None
        code = errs[0].get("code") if isinstance(errs, list) and errs and isinstance(errs[0], dict) else None
        raise bad(exit=p.returncode, utility_code=code)
    items = out.get("items") if isinstance(out, dict) else None
    ok = isinstance(items, list) and all(isinstance(i, dict) and isinstance(i.get("id"), str) and isinstance(i.get("markdown"), str) for i in items)
    if not ok:
        raise bad(reason="expected {items: [{id, markdown}]}")
    return items


def dispatch(root, entry, env):
    """Route by `provider:` else `type` -> ("items", [{id, markdown}]) | ("mcp", request) | ("manual", hint); typed MechanicError otherwise."""
    by_provider = bool(entry.get("provider"))
    key = entry["provider"] if by_provider else entry["type"]
    name = (not by_provider and ROUTES.get(key)) or f"utility-{key}-read"
    path = _script(name, env)
    integration = vault_io.resolve(root, f"anatomy/integrations/{key}.md") if re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", key) else None
    integration = integration if integration and os.path.isfile(integration) else None
    if not (path or integration or entry.get("fallback")):
        raise MechanicError("UNKNOWN_PROVIDER" if by_provider else "UNKNOWN_TYPE", **{"provider" if by_provider else "type": key})
    if path:
        return "items", _run_utility(name, path, root, entry, env)
    if _fallback(entry, integration) == "mcp":
        return "mcp", {"provider": key, "profile": entry.get("profile"), "url": entry["url"], "utility": name}
    return "manual", {"url": entry["url"], "utility": name, "hint": "utility unavailable: drop the content into _ingest/ manually"}
