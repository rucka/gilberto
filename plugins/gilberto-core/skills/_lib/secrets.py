import json
import os
import re
import shutil
import subprocess
import sys

from .connector import ConnectorError

_SEG = re.compile(r"[a-z0-9][a-z0-9_-]*")
_REF = re.compile(r"keychain:gilberto/([^/]+)/([^/]+)")
_VAR = "GILBERTO_SECRET"


def _key(provider, profile):
    for seg in (provider, profile):
        if not isinstance(seg, str) or not _SEG.fullmatch(seg):
            raise ConnectorError("provider", reason="provider/profile must match ^[a-z0-9][a-z0-9_-]*$")
    return provider, profile


def _check(value):
    if not isinstance(value, str) or not value:
        raise ConnectorError("provider", reason="secret value must be a non-empty string")


def parse_ref(ref):
    m = _REF.fullmatch(ref) if isinstance(ref, str) else None
    if not m:
        raise ConnectorError("provider", reason="ref must be keychain:gilberto/<provider>/<profile>")
    return _key(*m.groups())


def resolve(ref):
    return get(*parse_ref(ref))


def _run(argv, stdin=None):
    return subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=15)


def _cmds(service):
    """(set, get, delete) argv + set stdin builder, or None when no keychain backend is usable."""
    if sys.platform == "darwin" and shutil.which("security"):
        base = ["-s", service, "-a", "gilberto"]
        return (
            ["security", "-i"], lambda hexv: f"add-generic-password -U -s {service} -a gilberto -w {hexv}\n",
            ["security", "find-generic-password", *base, "-w"],
            ["security", "delete-generic-password", *base],
        )
    if sys.platform.startswith("linux") and shutil.which("secret-tool"):
        return (
            ["secret-tool", "store", "--label", service, "service", service], lambda hexv: hexv,
            ["secret-tool", "lookup", "service", service],
            ["secret-tool", "clear", "service", service],
        )
    return None


def _kc(op, service, hexv=None):
    """Keychain op -> stdout (get) / True; None on any failure or absence of backend."""
    cmds = _cmds(service)
    if not cmds:
        return None
    set_argv, mk_in, get_argv, del_argv = cmds
    try:
        if op == "set":
            r = _run(set_argv, mk_in(hexv))
        else:
            r = _run(get_argv if op == "get" else del_argv)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() if op == "get" else True


def _path(provider, profile):
    return os.path.join(os.path.expanduser("~"), ".config", "gilberto", "secrets", provider, f"{profile}.env")


def _write_file(path, value):
    d = os.path.dirname(path)
    os.makedirs(d, mode=0o700, exist_ok=True)
    os.chmod(d, 0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(f"{_VAR}={json.dumps(value)}\n")


def _read_file(path):
    try:
        mode = os.stat(path).st_mode & 0o777
    except FileNotFoundError:
        return None
    if mode & 0o077:
        raise ConnectorError("auth", path=path, fix=f"chmod 600 {path}", reason=f"secret file mode {mode:04o} too open")
    with open(path, encoding="utf-8") as f:
        line = f.read().strip()
    prefix = f"{_VAR}="
    try:
        if line.startswith(prefix):
            return json.loads(line[len(prefix):])
    except ValueError:
        pass
    raise ConnectorError("auth", path=path, reason="secret file malformed")


def set(provider, profile, value):  # noqa: A001
    provider, profile = _key(provider, profile)
    _check(value)
    if _kc("set", f"gilberto/{provider}/{profile}", value.encode().hex()):
        return
    _write_file(_path(provider, profile), value)


def get(provider, profile):
    provider, profile = _key(provider, profile)
    hexv = _kc("get", f"gilberto/{provider}/{profile}")
    if hexv:
        try:
            return bytes.fromhex(hexv).decode()
        except ValueError:
            pass
    value = _read_file(_path(provider, profile))
    if value is None:
        raise ConnectorError("not-found", provider=provider, profile=profile)
    return value


def delete(provider, profile):
    provider, profile = _key(provider, profile)
    _kc("delete", f"gilberto/{provider}/{profile}")
    try:
        os.remove(_path(provider, profile))
    except FileNotFoundError:
        pass
