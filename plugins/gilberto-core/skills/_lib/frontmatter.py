import json
import re

_FM = re.compile(r"\A---\n(.*?)\n---\n?", re.S)


def _value(raw):
    raw = raw.strip()
    try:
        return json.loads(raw)
    except ValueError:
        pass
    if raw.startswith("[") and raw.endswith("]"):
        return [v.strip().strip("'\"") for v in raw[1:-1].split(",") if v.strip()]
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        return raw[1:-1]
    return raw


def parse(text):
    """-> (frontmatter dict, body). Supports `key: scalar|flow-list` lines."""
    m = _FM.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep and not line.startswith((" ", "-", "#")):
            fm[k.strip()] = _value(v)
    return fm, text[m.end():]


def dump(fm, body):
    lines = "\n".join(f"{k}: {json.dumps(v)}" for k, v in fm.items())
    return f"---\n{lines}\n---\n{body}"


def set_key(text, key, value):
    """Replace/add one frontmatter line, leaving everything else byte-identical."""
    m = _FM.match(text)
    line = f"{key}: {json.dumps(value)}"
    if not m:
        return f"---\n{line}\n---\n{text}"
    block = m.group(1)
    pat = re.compile(rf"^{re.escape(key)}:.*$", re.M)
    block = pat.sub(line, block, count=1) if pat.search(block) else f"{block}\n{line}"
    return f"---\n{block}\n---\n" + text[m.end():]
