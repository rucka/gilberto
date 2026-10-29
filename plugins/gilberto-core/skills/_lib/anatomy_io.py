import re

from . import vault_io
from .result import MechanicError

TOPICS = "anatomy/topics.md"
ANATOMY = "anatomy/anatomy.md"
_TYPES = re.compile(r"^## Types\n(.*?)(?=^## |\Z)", re.S | re.M)


def read(root, rel):
    try:
        with open(vault_io.resolve(root, rel), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise MechanicError("REGISTRY_NOT_FOUND", file=rel)


def render(text, slug, title, date):
    return text.replace("{{SLUG}}", slug).replace("{{TITLE}}", title).replace("{{DATE}}", date)


def _cell(line):
    return line.strip().strip("|").split("|")[0].strip()


def has_topic(text, slug):
    rows = [l for l in text.split("\n") if l.startswith("|")]
    return any(_cell(l) == slug for l in rows[2:])


def append_topic(text, slug, description=""):
    description = " ".join(description.replace("|", "\\|").split())
    row = f"| {slug} | {description} |"
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("|")), None)
    if start is None:
        sep = "" if text.endswith("\n\n") or not text else ("\n" if text.endswith("\n") else "\n\n")
        return f"{text}{sep}| Topic | Description |\n| ----- | ----------- |\n{row}\n"
    end = start
    while end + 1 < len(lines) and lines[end + 1].startswith("|"):
        end += 1
    lines.insert(end + 1, row)
    return "\n".join(lines)


def _section(text, file=ANATOMY):
    m = _TYPES.search(text)
    if not m:
        raise MechanicError("REGISTRY_NOT_FOUND", file=file, section="## Types")
    return m


FIELD = re.compile(r"[a-z_][a-z0-9_-]{0,63}")
_ITEM = re.compile(r"""\s*(?:"([^"]*)"|'([^']*)'|([^\s"',\[\]#]+))\s*""")


def _span(body, name):
    """-> (start, end) of the `### <name>` block (heading .. next heading/section end) in body, or None."""
    m = re.search(rf"^### {re.escape(name)}[ \t]*$", body, re.M)
    if not m:
        return None
    nxt = re.compile(r"^#{1,3} ", re.M).search(body, m.end())
    return m.start(), nxt.start() if nxt else len(body)


def _item(raw, bad):
    m = _ITEM.fullmatch(raw)
    v = m and next(g for g in m.groups() if g is not None)
    if not v or not FIELD.fullmatch(v):
        raise bad
    return v


def _parse_schema(block, name):
    """Accepts YAML block lists (any indent) and flow lists, quoted or not, `#` comments; else INVALID_TYPE_BLOCK."""
    bad = MechanicError("INVALID_TYPE_BLOCK", type=name)
    m = re.search(r"^```ya?ml[ \t]*\n(.*?)^```[ \t]*$", block, re.S | re.M)
    if not m:
        raise bad
    schema, key = {}, None
    for line in m.group(1).splitlines():
        line = re.sub(r"(^|\s)#.*$", "", line).rstrip()
        if not line:
            continue
        item = re.fullmatch(r"\s*-\s+(.*)", line)
        if item:
            if key is None:
                raise bad
            schema[key].append(_item(item.group(1), bad))
            continue
        kv = re.fullmatch(r"(required|optional):\s*(.*)", line)
        if not kv or kv.group(1) in schema:
            raise bad
        key, rest = kv.groups()
        schema[key] = []
        if rest:
            if not (rest.startswith("[") and rest.endswith("]")):
                raise bad
            inner = rest[1:-1]
            schema[key] = [_item(i, bad) for i in inner.split(",")] if inner.strip() else []
            key = None
    if "required" not in schema:
        raise bad
    return schema


def render_schema(schema):
    out = []
    for key in ("required", "optional"):
        items = schema.get(key, [])
        if not items and key == "optional":
            continue
        out.append(f"{key}:" + ("" if items else " []"))
        out.extend(f"  - {i}" for i in items)
    return "\n".join(out) + "\n"


def get_type(text, name):
    """-> {required, optional} of the `### <name>` block under `## Types`, or None."""
    body = _section(text).group(1)
    span = _span(body, name)
    if not span:
        return None
    schema = _parse_schema(body[span[0] : span[1]], name)
    return {"required": schema["required"], "optional": schema.get("optional", [])}


def type_schema(text, name):
    """Like get_type, but None when `## Types` is absent (consumers: no schema = no check)."""
    return get_type(text, name) if _TYPES.search(text) else None


def append_type(text, name, schema):
    m = _section(text)
    body = m.group(1)
    head = body.rstrip("\n")
    tail = body[len(head):] or "\n"
    block = f"### {name}\n\n```yaml\n{render_schema(schema)}```"
    new = f"{head}\n\n{block}{tail}" if head else f"\n{block}{tail}"
    return text[: m.start(1)] + new + text[m.end(1):]


def merge_type(text, name, schema):
    """Union required/optional (existing order kept, new appended) -> (text, added)."""
    old = get_type(text, name)
    required = old["required"] + [k for k in schema["required"] if k not in old["required"]]
    optional = [k for k in old["optional"] + schema.get("optional", []) if k not in required]
    optional = list(dict.fromkeys(optional))
    merged = {"required": required, "optional": optional}
    added = {k: [i for i in merged[k] if i not in old[k]] for k in merged}
    m = _section(text)
    body = m.group(1)
    s, e = _span(body, name)
    tail = body[s:e][len(body[s:e].rstrip("\n")) :] or "\n"
    body = body[:s] + f"### {name}\n\n```yaml\n{render_schema(merged)}```{tail}" + body[e:]
    return text[: m.start(1)] + body + text[m.end(1):], added


_LEVELS = re.compile(r"^## Relationship levels\n(.*?)(?=^## |\Z)", re.S | re.M)
_LEVEL_LINE = re.compile(r"(?:[-*]\s+)?([a-z0-9][a-z0-9-]*)\s+—\s")


def _levels(text):
    m = _LEVELS.search(text)
    if not m:
        raise MechanicError("REGISTRY_NOT_FOUND", file=ANATOMY, section="## Relationship levels")
    return m


def level_names(text):
    """Names under `## Relationship levels`: table rows (header+separator skipped) and `name — criteria` lines."""
    names, row = [], 0
    for line in _levels(text).group(1).split("\n"):
        if line.startswith("|"):
            row += 1
            if row > 2:
                names.append(_cell(line))
            continue
        row = 0
        m = _LEVEL_LINE.match(line)
        if m:
            names.append(m.group(1))
    return names


def append_level(text, name, criteria):
    """Append after the last existing entry: a table row when the section holds a table, else a `- name — criteria` line."""
    m = _levels(text)
    body = m.group(1)
    lines = body.split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("|")), None)
    if start is not None:
        end = start
        while end + 1 < len(lines) and lines[end + 1].startswith("|"):
            end += 1
        lines.insert(end + 1, f"| {name} | {criteria.replace('|', chr(92) + '|')} |")
        new = "\n".join(lines)
    else:
        entry = f"- {name} — {criteria}"
        head = body.rstrip("\n")
        new = f"{head}\n{entry}{body[len(head):] or chr(10)}" if head else f"\n{entry}\n{body}"
    return text[: m.start(1)] + new + text[m.end(1):]
