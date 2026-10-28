import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import frontmatter, result, validate, vault_io  # noqa: E402
from _lib.atomic_write import Transaction, atomic_write  # noqa: E402
from _lib.result import MechanicError  # noqa: E402


def _run(argv, env):
    p = result.ArgParser(prog="mechanic-vault-collapse")
    p.add_argument("--path", required=True)
    a = p.parse_args(argv)
    root = vault_io.vault_root(env)
    parts = validate.rel_path(root, a.path)
    name = parts[-1]
    folder = vault_io.resolve(root, a.path)
    note = vault_io.resolve(root, f"{a.path}/{name}.md")
    sidecar = vault_io.resolve(root, f"{a.path}/.{name}.json")
    dst = vault_io.resolve(root, f"{a.path}.md")

    if not os.path.isfile(note):
        if os.path.isfile(dst) and not os.path.isdir(folder):
            result.log("already collapsed")
            return [], [f"{a.path}.md"]
        raise MechanicError("ENTITY_NOT_FOUND", path=a.path)
    if os.path.exists(dst):
        raise MechanicError("CONFLICT", path=a.path, existing=f"{a.path}.md")
    # the vault-new sidecar belongs to the entity; any other child (hidden included) blocks (D-11)
    children = sorted(c for c in os.listdir(folder) if c not in (f"{name}.md", f".{name}.json"))
    if children:
        raise MechanicError("HAS_CHILDREN", children=children)

    with open(note, encoding="utf-8") as f:
        original = f.read()
    side = None
    if os.path.exists(sidecar):
        with open(sidecar, encoding="utf-8") as f:
            side = f.read()
    text = frontmatter.set_key(original, "updated", datetime.date.today().isoformat())
    try:
        with Transaction() as t:
            t.write(dst, text)
            try:
                os.unlink(note)
                if side is not None:
                    os.unlink(sidecar)
                os.rmdir(folder)
            except BaseException:
                os.makedirs(folder, exist_ok=True)
                if not os.path.exists(note):
                    atomic_write(note, original)
                if side is not None and not os.path.exists(sidecar):
                    atomic_write(sidecar, side)
                raise
    except OSError as e:
        result.log(f"write failed ({e}); rolled back")
        raise MechanicError("WRITE_FAILED", error=str(e), rolledBack=True)
    return [f"{a.path}.md"], []


def main(argv=None, env=None):
    return result.run(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)


if __name__ == "__main__":
    sys.exit(main())
