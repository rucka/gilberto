import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import frontmatter, result, validate, vault_io  # noqa: E402
from _lib.atomic_write import Transaction  # noqa: E402
from _lib.result import MechanicError  # noqa: E402


def _run(argv, env):
    p = result.ArgParser(prog="mechanic-vault-promote")
    p.add_argument("--path", required=True)
    a = p.parse_args(argv)
    root = vault_io.vault_root(env)
    parts = validate.rel_path(root, a.path, ".md")
    name = parts[-1]
    parent = "/".join(parts[:-1])
    src = vault_io.resolve(root, a.path)
    folder = vault_io.resolve(root, f"{parent}/{name}")
    dst = vault_io.resolve(root, f"{parent}/{name}/{name}.md")
    rel = f"{parent}/{name}"

    if not os.path.isfile(src):
        if os.path.isfile(dst):
            result.log("already promoted")
            return [], [f"{rel}/{name}.md"]
        raise MechanicError("ENTITY_NOT_FOUND", path=a.path)
    if os.path.exists(dst):
        raise MechanicError("CONFLICT", path=a.path, existing=f"{rel}/{name}.md")

    with open(src, encoding="utf-8") as f:
        text = frontmatter.set_key(f.read(), "updated", datetime.date.today().isoformat())
    written = []
    try:
        with Transaction() as t:
            if not os.path.isdir(folder):
                t.mkdir(folder)
                written.append(rel)
            t.write(dst, text)
            os.unlink(src)
            written.append(f"{rel}/{name}.md")
    except OSError as e:
        result.log(f"write failed ({e}); rolled back")
        raise MechanicError("WRITE_FAILED", error=str(e), rolledBack=True)
    return written, []


def main(argv=None, env=None):
    return result.run(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)


if __name__ == "__main__":
    sys.exit(main())
