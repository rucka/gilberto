import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import result, vault_io  # noqa: E402

PLAYBOOKS = "anatomy/playbooks"
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
    return [(u, f) for u, f in out]


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
