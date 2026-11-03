import datetime
import json
import os
import re
import time

from . import frontmatter, result
from .atomic_write import atomic_write
from .result import MechanicError

CODES = ("auth", "rate-limit", "not-found", "provider", "profile-unresolved")
TYPE = "intelligence-source"
_PROFILE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}:[a-z0-9][a-z0-9-]{0,63}")


class ConnectorError(MechanicError):
    def __init__(self, code, **extra):
        if code not in CODES:
            raise ValueError(f"unknown connector error code: {code}")
        super().__init__(code, **extra)


def normalize_item(md, source, profile, type=TYPE, created=None):
    """Markdown (with or without frontmatter) -> canonical frontmatter `type, source, created, source_profile` (profile = `<provider>:<profile>`)."""
    if not isinstance(profile, str) or not _PROFILE.fullmatch(profile):
        raise ConnectorError("provider", reason="profile must be <provider>:<profile>", profile=profile)
    fm, body = frontmatter.parse(md)
    fm.update(type=type, source=source, created=fm.get("created") or created or datetime.date.today().isoformat(), source_profile=profile)
    return frontmatter.dump(fm, body)


def run_utility(fn, argv, env):
    """fn(argv, env) -> items; stdout `{items}` exit 0, or `{errors:[{code}]}` exit 1 (stray OSError -> `provider`)."""
    try:
        items = fn(argv, env)
    except ConnectorError as e:
        result.log(f"error: {e.code}")
        print(json.dumps({"errors": [e.as_dict()]}))
        return 1
    except OSError as e:
        result.log(f"error: provider ({e})")
        print(json.dumps({"errors": [{"code": "provider"}]}))
        return 1
    print(json.dumps({"items": list(items)}))
    return 0


def retry(fn, attempts=3, base=0.5, sleep=time.sleep):
    """Call fn; rate-limit and transient (OSError) failures back off base*2^n, then re-raise the last."""
    for n in range(attempts):
        try:
            return fn()
        except (ConnectorError, OSError) as e:
            if isinstance(e, ConnectorError) and e.code != "rate-limit" or n == attempts - 1:
                raise
            sleep(base * 2**n)


def load_state(path):
    """`{url: {fetched: [ids]}}`; missing/corrupt file or entry -> empty."""
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(state, dict):
        return {}
    return {u: v for u, v in state.items() if isinstance(v, dict) and isinstance(v.get("fetched"), list)}


def save_state(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    atomic_write(path, json.dumps(state, indent=2, sort_keys=True) + "\n")


def new_items(state, url, items):
    """Items whose id is not yet fetched for url; records them in state."""
    fetched = state.setdefault(url, {"fetched": []})["fetched"]
    fresh = []
    for item in items:
        if item["id"] not in fetched:
            fetched.append(item["id"])
            fresh.append(item)
    return fresh
