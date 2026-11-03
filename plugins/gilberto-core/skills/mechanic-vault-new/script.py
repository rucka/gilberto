import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import frontmatter, result, validate, vault_io  # noqa: E402
from _lib.atomic_write import Transaction  # noqa: E402
from _lib.result import MechanicError  # noqa: E402

UNCATEGORIZED = "_uncategorized"
TEMPLATE_META = ("scope", "description")  # template-only keys (mechanic-forge-template), not copied to notes


def _parse(argv):
    p = result.ArgParser(prog="mechanic-vault-new")
    p.add_argument("--pillar", required=True)
    p.add_argument("--template", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--frontmatter", default="{}")
    p.add_argument("--path")
    p.add_argument("--force", action="store_true")
    return p.parse_args(argv)


def _supplied(raw):
    try:
        fm = json.loads(raw)
    except ValueError:
        fm = None
    if not isinstance(fm, dict):
        raise MechanicError("INVALID_FRONTMATTER", reason="--frontmatter must be a JSON object")
    return fm


def _segments(path):
    parts = path.split("/") if isinstance(path, str) else []
    if len(parts) != 2:
        raise MechanicError("INVALID_SLUG", input=path)
    for i, p in enumerate(parts):
        if not (i == 0 and p == UNCATEGORIZED):
            validate.slug(p)
    return parts


def render(root, pillar, template, supplied, today):
    """New-note content: (ordered frontmatter, body) from the pillar template + supplied keys."""
    tpl = vault_io.resolve(root, f"anatomy/templates/{pillar}/{template}/{template}.md")
    if not os.path.isfile(tpl):
        raise MechanicError("TEMPLATE_NOT_FOUND", template=template, pillar=pillar)
    with open(tpl, encoding="utf-8") as f:
        tpl_fm, body = frontmatter.parse(f.read())
    tpl_fm = {k: v for k, v in tpl_fm.items() if k not in TEMPLATE_META}
    return _order(root, {**tpl_fm, **supplied, "created": today, "updated": today}), body


def _order(root, fm):
    validate.frontmatter(root, fm)
    ordered = {k: fm[k] for k in ("type", "topics")}
    ordered.update({k: v for k, v in fm.items() if k not in ("type", "topics", "created", "updated")})
    ordered.update(created=fm["created"], updated=fm["updated"])
    return ordered


def _run(argv, env):
    a = _parse(argv)
    root = vault_io.vault_root(env)
    validate.slug(a.slug)
    validate.slug(a.template)
    validate.pillar(root, a.pillar)
    nested = a.path is not None
    parent = f"{a.pillar}/{'/'.join(_segments(a.path))}" if nested else None
    rel = parent or f"{a.pillar}/{a.slug}"
    folder = vault_io.resolve(root, rel)
    note = os.path.join(folder, f"{a.slug}.md")
    sidecar = os.path.join(folder, f".{a.slug}.json")
    note_rel = f"{rel}/{a.slug}.md"
    today = datetime.date.today().isoformat()
    supplied = _supplied(a.frontmatter)

    exists = os.path.exists(note)
    if exists and not a.force:
        result.log("skipped (idempotent)")
        return [], [note_rel]

    if exists:
        with open(note, encoding="utf-8") as f:
            old_fm, body = frontmatter.parse(f.read())
        fm = {**old_fm, **supplied, "created": old_fm.get("created", today), "updated": today}
        fm = _order(root, fm)
    else:
        fm, body = render(root, a.pillar, a.template, supplied, today)

    written = []
    try:
        with Transaction() as t:
            t.mkdir(folder)
            written += [os.path.relpath(d, root) for d in t.dirs]
            t.write(note, frontmatter.dump(fm, body))
            written.append(note_rel)
            if not nested and not os.path.exists(sidecar):
                t.write(sidecar, json.dumps({"slug": a.slug, "pillar": a.pillar, "template": a.template}) + "\n")
                written.append(f"{rel}/.{a.slug}.json")
    except OSError as e:
        result.log(f"write failed ({e}); rolled back")
        raise MechanicError("WRITE_FAILED", error=str(e), rolledBack=True)
    return written, []


def main(argv=None, env=None):
    return result.run(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)


if __name__ == "__main__":
    sys.exit(main())
