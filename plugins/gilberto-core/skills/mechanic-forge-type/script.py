import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import anatomy_io, result, validate, vault_io  # noqa: E402
from _lib.atomic_write import Transaction  # noqa: E402
from _lib.result import MechanicError  # noqa: E402


def _parse(argv):
    p = result.ArgParser(prog="mechanic-forge-type")
    p.add_argument("--name", required=True)
    p.add_argument("--scope")
    p.add_argument("--schema", required=True)
    p.add_argument("--merge", action="store_true")
    return p.parse_args(argv)


def _composite(scope, name):
    validate.slug(name)
    if scope is None:
        if name in validate.DIRECT_TYPES:
            return name
        raise MechanicError("INVALID_SCOPE", scope=None, name=name)
    validate.slug(scope)
    if scope not in validate.SCOPES:
        raise MechanicError("INVALID_SCOPE", scope=scope)
    return f"{scope}-{name}"


def _schema(raw):
    try:
        s = json.loads(raw)
    except ValueError:
        s = None

    def bad(reason):
        return MechanicError("INVALID_SCHEMA", reason=reason, input=raw)

    if not isinstance(s, dict):
        raise bad("schema must be a JSON object")
    unknown = sorted(set(s) - {"required", "optional"})
    if unknown:
        raise bad(f"unknown keys {unknown}")
    if "required" not in s:
        raise bad("required is mandatory")
    for k in s:
        if not isinstance(s[k], list) or not all(isinstance(i, str) and anatomy_io.FIELD.fullmatch(i) for i in s[k]):
            raise bad(f"{k} must be an array of field names ({anatomy_io.FIELD.pattern})")
    return {k: list(dict.fromkeys(s.get(k, []))) for k in ("required", "optional")}


def _run(argv, env):
    a = _parse(argv)
    root = vault_io.vault_root(env)
    name = _composite(a.scope, a.name)
    schema = _schema(a.schema)
    path = vault_io.resolve(root, anatomy_io.ANATOMY)
    text = anatomy_io.read(root, anatomy_io.ANATOMY)
    old = anatomy_io.get_type(text, name)

    if old is None:
        new = anatomy_io.append_type(text, name, schema)
    elif {k: set(v) for k, v in old.items()} == {k: set(v) for k, v in schema.items()}:
        new = text
    elif not a.merge:
        raise MechanicError("TYPE_CONFLICT", type=name, existing=old, supplied=schema)
    else:
        new, added = anatomy_io.merge_type(text, name, schema)
        result.log(f"merged {name}: +required{added['required']} +optional{added['optional']}")

    if new == text:
        result.log("skipped (idempotent)")
        return [], [anatomy_io.ANATOMY]
    try:
        with Transaction() as t:
            t.write(path, new)
    except OSError as e:
        result.log(f"write failed ({e}); rolled back")
        raise MechanicError("WRITE_FAILED", error=str(e), rolledBack=True)
    return [anatomy_io.ANATOMY], []


def main(argv=None, env=None):
    return result.run(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)


if __name__ == "__main__":
    sys.exit(main())
