import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import frontmatter, integrations, result, vault_io  # noqa: E402
from _lib.atomic_write import atomic_write  # noqa: E402
from _lib.connector import ConnectorError  # noqa: E402
from _lib.result import MechanicError  # noqa: E402

PLAYBOOKS = "anatomy/playbooks"
SKILLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTES = {"rss": "utility-fetch-rss", "atom": "utility-fetch-rss", "http": "utility-download-html"}
TIMEOUT = 120
_FENCE = re.compile(r"^```ya?ml[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)
_TOP = re.compile(r'^(?:("(?:[^"\\\n]|\\.)*")|(https?://\S+?)):[ \t]*$')
_SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
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
                try:
                    cur = [json.loads(top.group(1)) if top.group(1) else top.group(2), {}]
                except ValueError:
                    cur = [None, None]
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
    """Called only for a `provider:` entry without `profile:`: explicit > folder note `connectors:` walking up from the entry's `target` (else its pillar) > preferences > MechanicError("PROFILE_UNRESOLVED")."""
    try:
        return integrations.resolve_profile(root, entry.get("target") or entry["pillar"], entry["provider"])
    except ConnectorError:
        raise MechanicError("PROFILE_UNRESOLVED", provider=entry["provider"])


def _utility_dirs(env):
    return [d for d in env.get("GILBERTO_UTILITY_PATH", "").split(os.pathsep) if d] + [SKILLS]


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
    return value


def _run_utility(name, path, root, entry, env, profile):
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
    if not _SLUG.fullmatch(key):
        raise MechanicError("INVALID_PROVIDER" if by_provider else "INVALID_TYPE", **{"provider" if by_provider else "type": key})
    name = (not by_provider and ROUTES.get(key)) or f"utility-{key}-read"
    path = _script(name, env)
    profile, unresolved = entry.get("profile"), None
    if by_provider and not profile:
        try:
            profile = resolve_profile(root, entry)
        except MechanicError as e:
            unresolved = e
    integration = integrations.integration_path(root, key, profile)
    if not (path or integration or entry.get("fallback")):
        raise MechanicError("UNKNOWN_PROVIDER" if by_provider else "UNKNOWN_TYPE", **{"provider" if by_provider else "type": key})
    runner = integrations.resolve_runner(path, None if path else _fallback(entry, integration))
    if runner["kind"] == "script":
        if unresolved:
            raise unresolved
        items = _run_utility(name, path, root, entry, env, profile)
        if by_provider:
            items = [{**i, "markdown": frontmatter.set_key(i["markdown"], "source_profile", f"{key}:{profile}")} for i in items]
        return "items", items
    if runner["reason"] == "mcp-fallback":
        return "mcp", {"provider": key, "profile": profile, "url": entry["url"], "utility": name}
    return "manual", {"url": entry["url"], "utility": name, "hint": runner["hint"]}


def _load_state(root, e):
    rel = f"{PLAYBOOKS}/{e['pillar']}/sources/{e['contributor']}/_state.json"
    path = vault_io.resolve(root, rel)
    if not os.path.exists(path):
        return rel, path, {}
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, dict):
            raise ValueError("not an object")
    except ValueError as ex:
        raise MechanicError("STATE_CORRUPT", file=rel, error=str(ex))
    return rel, path, state


def _fetched(state, url):
    value = state.get(url, {})
    if not isinstance(value, dict):
        raise MechanicError("STATE_CORRUPT", url=url, error="entry is not an object")
    fetched = value.get("fetched", [])
    if not isinstance(fetched, list):
        raise MechanicError("STATE_CORRUPT", url=url, error="fetched is not a list")
    return fetched


def _write_items(root, e, items, state, written, skipped):
    fetched = _fetched(state, e["url"])
    for item in items:
        digest = hashlib.sha1(f"{e['url']}\0{item['id']}".encode()).hexdigest()[:12]
        rel = f"_ingest/{e['contributor']}-{digest}.md"
        if item["id"] in fetched:
            skipped.append({"path": rel, "reason": "already-fetched"})
            continue
        path = vault_io.resolve(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        atomic_write(path, item["markdown"])
        fetched.append(item["id"])
        state[e["url"]] = {"fetched": fetched}
        written.append(rel)


def _fetch_one(root, e, env, written, skipped):
    state_rel, state_path, state = _load_state(root, e)
    before = json.dumps(state, sort_keys=True)
    try:
        kind, payload = dispatch(root, e, env)
        if kind == "items":
            _write_items(root, e, payload, state, written, skipped)
        else:
            skipped.append({"source": e["file"], "url": e["url"], "reason": "mcp-fallback" if kind == "mcp" else "manual", **payload})
    finally:
        if json.dumps(state, sort_keys=True) != before:
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            atomic_write(state_path, json.dumps(state, indent=2, sort_keys=True) + "\n")


def _run(argv, env):
    p = result.ArgParser(prog="gilberto-capability-fetch")
    p.add_argument("--pillar")
    p.add_argument("--source")
    a = p.parse_args(argv)
    root = vault_io.vault_root(env)
    entries, errors = load_sources(root, a.pillar, a.source)
    written, skipped = [], []
    for e in entries:
        try:
            _fetch_one(root, e, env, written, skipped)
        except MechanicError as ex:
            errors.append({**ex.as_dict(), "source": e["file"], "url": e["url"]})
        except OSError as ex:
            errors.append({"code": "WRITE_FAILED", "source": e["file"], "url": e["url"], "error": str(ex)})
    return written, skipped, errors


def main(argv=None, env=None):
    argv = sys.argv[1:] if argv is None else argv
    env = os.environ if env is None else env
    try:
        written, skipped, errors = _run(argv, env)
    except MechanicError as e:
        result.log(f"error: {e.code}")
        result.emit("error", errors=[e.as_dict()])
        return 1
    status = ("error" if not (written or skipped) else "partial") if errors else "skipped" if skipped and not written else "ok"
    result.emit(status, written, skipped, errors)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
