import os
import re

from .result import MechanicError

SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
PILLARS = ("me", "pulse", "projects", "intelligence", "journey", "network")
# "project": AC1 example uses `project-index` next to the seeded `projects-index`; both accepted (ADL)
SCOPES = ("anatomy", "pillar", "me", "pulse", "projects", "project", "intelligence", "journey", "network")
DIRECT_TYPES = ("person", "company")
MANDATORY = ("type", "topics", "created", "updated")


def slug(value):
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise MechanicError("INVALID_SLUG", input=value)
    return value


def pillar(root, name):
    if name not in PILLARS or not os.path.isdir(os.path.join(root, name)):
        raise MechanicError("PILLAR_NOT_FOUND", pillar=name)
    return name


def rel_path(root, raw, suffix=""):
    """Validate a vault-relative `<pillar>/<slug>[/...]<suffix>` path; -> list of slug components."""
    if not isinstance(raw, str) or not raw.endswith(suffix):
        raise MechanicError("INVALID_SLUG", input=raw)
    parts = (raw[: len(raw) - len(suffix)] if suffix else raw).split("/")
    if len(parts) < 2:
        raise MechanicError("INVALID_SLUG", input=raw)
    for p in parts:
        if not SLUG.fullmatch(p):
            raise MechanicError("INVALID_SLUG", input=raw)
    pillar(root, parts[0])
    return parts


def _registered_fields(root, type_):
    """Optional `Fields` column of the `## Types` table in anatomy/anatomy.md; None = not registered / no schema."""
    try:
        with open(os.path.join(root, "anatomy", "anatomy.md"), encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return None
    section = re.search(r"^## Types\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not section:
        return None
    header = None
    for line in section.group(1).splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
        elif cells[0] == type_ and "fields" in header:
            fields = cells[header.index("fields")]
            return [f.strip() for f in fields.split(",") if f.strip()] or None
    return None


def frontmatter(root, fm):
    missing = [k for k in MANDATORY if k not in fm]
    if missing:
        raise MechanicError("INVALID_FRONTMATTER", missing=missing)
    t = fm["type"]
    scope, _, role = str(t).partition("-")
    if not (t in DIRECT_TYPES or (scope in SCOPES and SLUG.fullmatch(role or ""))):
        raise MechanicError("INVALID_FRONTMATTER", type=t, reason="unknown type scope")
    if not isinstance(fm["topics"], list):
        raise MechanicError("INVALID_FRONTMATTER", reason="topics must be a list")
    fields = _registered_fields(root, t)
    if fields is not None:
        allowed = set(MANDATORY) | set(fields)
        unknown = sorted(set(fm) - allowed)
        absent = [f for f in fields if f not in fm]
        if unknown or absent:
            raise MechanicError("INVALID_FRONTMATTER", type=t, diff={"missing": absent, "unknown": unknown})
    return fm
