import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import frontmatter, result, validate, vault_io  # noqa: E402
from _lib.atomic_write import Transaction  # noqa: E402
from _lib.result import MechanicError  # noqa: E402

PLACEHOLDER = "# {{TITLE}}\n\nslug: {{SLUG}}\ncreated: {{DATE}}\n"


def _parse(argv):
    p = result.ArgParser(prog="mechanic-forge-template")
    p.add_argument("--name", required=True)
    p.add_argument("--pillar", required=True)
    p.add_argument("--description", default="")
    return p.parse_args(argv)


def _run(argv, env):
    a = _parse(argv)
    root = vault_io.vault_root(env)
    validate.slug(a.name)
    if a.pillar not in validate.PILLARS:
        raise MechanicError("INVALID_PILLAR", pillar=a.pillar)
    rel = f"anatomy/templates/{a.pillar}/{a.name}"
    folder = vault_io.resolve(root, rel)
    files = {
        f"{rel}/template.md": frontmatter.dump({"scope": a.pillar, "description": a.description}, f"\n# {a.name}\n"),
        f"{rel}/files/note.md": PLACEHOLDER,
    }

    written, skipped = [], []
    try:
        with Transaction() as t:
            for d in (folder, os.path.join(folder, "files")):
                if not os.path.isdir(d):
                    t.mkdir(d)
                    written.append(os.path.relpath(d, root))
            for r, data in files.items():
                path = vault_io.resolve(root, r)
                if os.path.exists(path):
                    skipped.append(r)
                else:
                    t.write(path, data)
                    written.append(r)
    except OSError as e:
        result.log(f"write failed ({e}); rolled back")
        raise MechanicError("WRITE_FAILED", error=str(e), rolledBack=True)
    if not written:
        result.log("skipped (idempotent)")
    return written, skipped


def main(argv=None, env=None):
    return result.run(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)


if __name__ == "__main__":
    sys.exit(main())
