import datetime
import os
import re

from . import frontmatter, vault_io
from .atomic_write import atomic_write
from .connector import ConnectorError
from .result import MechanicError

KEYS = ("type", "provider", "profile", "accounts", "scopes", "channels", "cadence", "fallback", "auto_write", "secret", "created", "updated")
FALLBACKS = ("mcp", "none")
OPS = ("read", "search", "write", "send", "delete")
TASKS = "journey/tasks.md"
_SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_SECRET_PREFIX = re.compile(r"(xox[abprs]-|gh[pousr]_|github_pat_|sk-|AKIA|AIza|Bearer\s)")
_SECRET_BLOB = re.compile(r"[A-Za-z0-9+/_=-]{32,}")
_REF = re.compile(r"(keychain|file):[A-Za-z0-9._/~-]+")
_SEND = re.compile(r"(^|[:_.-])send($|[:_.-])")


def _slug(value, code="INVALID_PROFILE"):
    if not isinstance(value, str) or not _SLUG.fullmatch(value):
        raise MechanicError(code, input=value)
    return value


def _fm_block(text):
    m = frontmatter._FM.match(text)
    if not m and text.startswith("---"):
        raise ValueError("frontmatter is not closed")
    return m.group(1) if m else None


def validate_integration(path):
    """-> frontmatter of `anatomy/integrations/<provider>/<profile>.md`; typed INVALID_INTEGRATION on unknown keys, secret-looking values, malformed."""
    bad = lambda reason, **x: MechanicError("INVALID_INTEGRATION", path=os.path.basename(path), reason=reason, **x)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        block = _fm_block(text)
    except (OSError, ValueError) as e:
        raise bad(str(e))
    if block is None:
        raise bad("no frontmatter")
    for line in block.splitlines():
        if line.strip() and not line.startswith((" ", "\t", "-", "#")) and ":" not in line:
            raise bad("malformed frontmatter line", line=line)
    fm = frontmatter.parse(text)[0]
    unknown = [k for k in fm if k not in KEYS]
    if unknown:
        raise bad("unknown keys", keys=unknown)
    for k, v in fm.items():
        for s in v if isinstance(v, list) else [v]:
            s = str(s)
            if k == "secret":
                if not _REF.fullmatch(s):
                    raise bad("secret must be a reference (keychain:… or file:…), never a value", keys=[k])
            elif _SECRET_PREFIX.match(s) or _SECRET_BLOB.fullmatch(s):
                raise bad("secret-looking value", keys=[k])
    if "fallback" in fm and fm["fallback"] not in FALLBACKS:
        raise bad("fallback must be mcp|none", keys=["fallback"])
    auto = fm.get("auto_write", [])
    if not isinstance(auto, list) or any(_SEND.search(str(a)) for a in auto):
        raise bad("auto_write must be a list and never allowlists send", keys=["auto_write"])
    return fm


def integration_path(root, provider, profile=None):
    """`<provider>/<profile>.md` (profile default `default`), else flat `<provider>.md` (compat, `default` only); None when absent."""
    _slug(provider, "INVALID_PROVIDER")
    name = "default" if profile is None else _slug(profile)
    rels = [f"{provider}/{name}.md"] + ([f"{provider}.md"] if name == "default" else [])
    for rel in rels:
        path = vault_io.resolve(root, f"anatomy/integrations/{rel}")
        if os.path.isfile(path):
            return path


def _unq(s):
    s = s.strip()
    return s[1:-1] if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"" else s


def _connectors(block):
    out, in_block = {}, False
    for line in block.splitlines():
        m = re.match(r"connectors:[ \t]*(.*?)[ \t]*$", line)
        if m:
            val = m.group(1)
            if val.startswith("{") and val.endswith("}"):
                for part in val[1:-1].split(","):
                    k, _, v = part.partition(":")
                    if k.strip() and v.strip():
                        out[_unq(k)] = _unq(v)
                return out
            in_block = not val
            continue
        kv = in_block and re.match(r"[ \t]+([^:\s]+):[ \t]*(.*?)[ \t]*$", line)
        if kv:
            out[_unq(kv[1])] = _unq(kv[2])
        elif line.strip() and not line[0].isspace():
            in_block = False
    return out


def _folder_note(root, d):
    note = os.path.join(d, os.path.basename(d) + ".md")
    if d == root or not os.path.isfile(note):
        return {}
    try:
        with open(note, encoding="utf-8") as f:
            block = _fm_block(f.read())
    except (OSError, ValueError) as e:
        raise MechanicError("INVALID_FOLDER_NOTE", path=os.path.relpath(note, root), reason=str(e))
    return _connectors(block or "")


def _preferences(root, provider):
    path = vault_io.resolve(root, "anatomy/preferences.md")
    if not os.path.isfile(path):
        return None
    on = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("## "):
                on = line.strip() == "## Integrations"
            m = on and re.fullmatch(rf"[-*]?[ \t]*{re.escape(provider)}:[ \t]*(\S+)[ \t]*", line.strip())
            if m:
                return m.group(1)


def resolve_profile(root, target, provider, explicit=None):
    """explicit > nearest folder note `connectors:` walking up from target (stops at vault root) > `preferences.md > ## Integrations` > ConnectorError(profile-unresolved); never a guess."""
    if explicit is not None:
        return _slug(explicit)
    start = vault_io.resolve(root, target)
    d = start if os.path.isdir(start) else os.path.dirname(start)
    while True:
        profile = _folder_note(root, d).get(provider)
        if profile:
            return _slug(profile)
        if d == root:
            break
        d = os.path.dirname(d)
    profile = _preferences(root, provider)
    if profile:
        return _slug(profile)
    raise ConnectorError("profile-unresolved", provider=provider)


def resolve_runner(script, fallback):
    """Script wins; else `fallback: mcp` -> skipped/mcp-fallback; else skipped/manual with an `_ingest/` hint."""
    if script:
        return {"kind": "script", "path": script}
    fallback = fallback or "none"
    if fallback not in FALLBACKS:
        raise MechanicError("INVALID_FALLBACK", fallback=fallback, allowed=list(FALLBACKS))
    if fallback == "mcp":
        return {"kind": "skipped", "reason": "mcp-fallback"}
    return {"kind": "skipped", "reason": "manual", "hint": "utility unavailable: drop the content into _ingest/ manually"}


def is_unattended(env):
    return env.get("GILBERTO_UNATTENDED") in ("1", "true")


def guard_write(root, provider, profile, op, action, unattended, auto_write=(), summary=""):
    """-> {decision: allow|confirm|pending}. Reads allow; a write allowlisted in `auto_write` (never a send) allows; else attended -> confirm,
    unattended -> no external call, one pending task appended (idempotent) to journey/tasks.md."""
    if op not in OPS:
        raise MechanicError("INVALID_OP", op=op, allowed=list(OPS))
    if op in ("read", "search") or (op != "send" and action in auto_write):
        return {"decision": "allow"}
    if not unattended:
        return {"decision": "confirm"}
    line = "- [ ] pending confirmation: " + " ".join(f"{provider}:{profile} {action} — {summary}".split())
    path = vault_io.resolve(root, TASKS)
    text = open(path, encoding="utf-8").read() if os.path.isfile(path) else f"---\ntype: tasks\ncreated: {datetime.date.today().isoformat()}\n---\n\n# Tasks\n"
    if line not in text.splitlines():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        atomic_write(path, text.rstrip("\n") + "\n" + line + "\n")
    return {"decision": "pending", "path": TASKS}
