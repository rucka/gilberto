import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import anatomy_io, result, validate, vault_io  # noqa: E402
from _lib.atomic_write import Transaction  # noqa: E402
from _lib.result import MechanicError  # noqa: E402


def _parse(argv):
    p = result.ArgParser(prog="mechanic-forge-relationship-level")
    p.add_argument("--name", required=True)
    p.add_argument("--criteria", required=True)
    return p.parse_args(argv)


def _run(argv, env):
    a = _parse(argv)
    root = vault_io.vault_root(env)
    validate.slug(a.name)
    criteria = " ".join(a.criteria.split())
    if not criteria:
        raise MechanicError("INVALID_CRITERIA", input=a.criteria)
    path = vault_io.resolve(root, anatomy_io.ANATOMY)
    text = anatomy_io.read(root, anatomy_io.ANATOMY)
    if a.name in anatomy_io.level_names(text):
        result.log("skipped (idempotent)")
        return [], [anatomy_io.ANATOMY]
    try:
        with Transaction() as t:
            t.write(path, anatomy_io.append_level(text, a.name, criteria))
    except OSError as e:
        result.log(f"write failed ({e}); rolled back")
        raise MechanicError("WRITE_FAILED", error=str(e), rolledBack=True)
    return [anatomy_io.ANATOMY], []


def main(argv=None, env=None):
    return result.run(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)


if __name__ == "__main__":
    sys.exit(main())
