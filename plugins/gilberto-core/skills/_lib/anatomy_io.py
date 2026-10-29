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


def _block(name):
    return re.compile(rf"^### {re.escape(name)}\n\n```yaml\n(.*?)```\n", re.S | re.M)


def _parse_schema(yaml):
    schema, key = {}, None
    for line in yaml.splitlines():
        if line.startswith("  - ") and key:
            schema[key].append(line[4:])
        elif line.endswith(":") or line.endswith(": []"):
            key = line.split(":")[0]
            schema[key] = []
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
    m = _block(name).search(_section(text).group(1))
    if not m:
        return None
    schema = _parse_schema(m.group(1))
    return {"required": schema.get("required", []), "optional": schema.get("optional", [])}


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
    body = _block(name).sub(
        lambda _: f"### {name}\n\n```yaml\n{render_schema(merged)}```\n", m.group(1), count=1
    )
    return text[: m.start(1)] + body + text[m.end(1):], added
