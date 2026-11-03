import subprocess

import pytest

from _lib import secrets
from _lib.connector import ConnectorError


class Keychain:
    """Stub keychain with per-op failure; absent delete -> security exit 44 / secret-tool exit 0."""

    def __init__(self, platform):
        self.platform, self.store, self.fail = platform, {}, set()

    def __call__(self, argv, stdin=None):
        def rc(code, out=""):
            return subprocess.CompletedProcess(argv, code, out, "")

        if argv[0] == "security" and argv[1] == "-i":
            if "set" in self.fail:
                return rc(1)
            parts = stdin.split()
            self.store[parts[parts.index("-s") + 1]] = parts[-1]
            return rc(0)
        if "store" in argv:
            if "set" in self.fail:
                return rc(1)
            self.store[argv[-1]] = stdin
            return rc(0)
        svc = next((argv[i + 1] for i, a in enumerate(argv) if a == "-s"), None) or argv[-1]
        if "find-generic-password" in argv or "lookup" in argv:
            if "get" in self.fail or svc not in self.store:
                return rc(1)
            return rc(0, self.store[svc] + "\n")
        if "delete" in self.fail:
            return rc(1)
        if svc not in self.store:
            return rc(44 if self.platform == "darwin" else 0)
        del self.store[svc]
        return rc(0)


@pytest.fixture(params=["darwin", "linux"])
def kc(request, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(secrets.sys, "platform", request.param)
    monkeypatch.setattr(secrets.shutil, "which", lambda n: "/bin/" + n)
    k = Keychain(request.param)
    monkeypatch.setattr(secrets, "_run", k)
    k.home = tmp_path
    k.file = tmp_path / ".config/gilberto/secrets/google/learnn.env"
    return k


def test_keychain_set_removes_stale_fallback_file(kc):  # r0-1 witness
    kc.fail.add("set")
    secrets.set("google", "learnn", "OLD")
    assert kc.file.exists()
    kc.fail.clear()
    secrets.set("google", "learnn", "NEW")
    assert not kc.file.exists()
    kc.fail.add("get")
    with pytest.raises(ConnectorError) as e:
        secrets.get("google", "learnn")
    assert e.value.code == "not-found"


def test_keychain_set_without_fallback_file_ok(kc):  # r0-1 control
    secrets.set("google", "learnn", "NEW")
    assert not kc.file.exists()
    assert secrets.get("google", "learnn") == "NEW"


def test_keychain_set_failure_keeps_fallback(kc):  # r0-1 control
    kc.fail.add("set")
    secrets.set("google", "learnn", "V")
    assert kc.file.exists()
    assert secrets.get("google", "learnn") == "V"


def test_delete_keychain_failure_raises(kc):  # r0-3 witness
    secrets.set("google", "learnn", "TOKEN")
    kc.fail.add("delete")
    with pytest.raises(ConnectorError) as e:
        secrets.delete("google", "learnn")
    assert e.value.code == "provider"
    kc.fail.clear()
    assert secrets.get("google", "learnn") == "TOKEN"


def test_delete_absent_in_keychain_idempotent(kc):  # r0-3 control
    secrets.delete("google", "learnn")
    secrets.delete("google", "learnn")


def test_delete_removes_keychain_and_file(kc):  # r0-3 control
    kc.fail.add("set")
    secrets.set("google", "learnn", "F")
    kc.fail.clear()
    kc.store["gilberto/google/learnn"] = b"K".hex()
    secrets.delete("google", "learnn")
    assert not kc.file.exists() and not kc.store
    with pytest.raises(ConnectorError) as e:
        secrets.get("google", "learnn")
    assert e.value.code == "not-found"


def test_delete_without_keychain_backend_removes_fallback(kc, monkeypatch):  # r0-3 control
    monkeypatch.setattr(secrets.shutil, "which", lambda n: None)
    secrets.set("google", "learnn", "F")
    assert kc.file.exists()
    secrets.delete("google", "learnn")
    assert not kc.file.exists()
    with pytest.raises(ConnectorError) as e:
        secrets.get("google", "learnn")
    assert e.value.code == "not-found"


@pytest.mark.parametrize("exc", [subprocess.TimeoutExpired("x", 15), OSError("boom")], ids=["timeout", "oserror"])
def test_delete_keychain_exception_raises(kc, monkeypatch, exc):  # r0-3 witness
    secrets.set("google", "learnn", "TOKEN")

    def boom(argv, stdin=None):
        if "delete-generic-password" in argv or "clear" in argv:
            raise exc
        return kc(argv, stdin)

    monkeypatch.setattr(secrets, "_run", boom)
    with pytest.raises(ConnectorError) as e:
        secrets.delete("google", "learnn")
    assert e.value.code == "provider"
    assert secrets.get("google", "learnn") == "TOKEN"
