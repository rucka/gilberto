import os

from .result import MechanicError


def vault_root(env):
    root = env.get("GILBERTO_ROOT")
    if not root or not os.path.isdir(root):
        raise MechanicError("INVALID_PATH", input=root, reason="GILBERTO_ROOT unset or not a directory")
    return os.path.realpath(root)


def resolve(root, rel):
    """Join rel under root; reject any real path escaping root."""
    target = os.path.realpath(os.path.join(root, rel))
    if target != root and not target.startswith(root + os.sep):
        raise MechanicError("INVALID_PATH", input=rel)
    return target
