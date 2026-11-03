import logging
import os
import stat
import subprocess
import sys

import pytest

from _lib import secrets
from _lib.connector import ConnectorError

VAL = 'p@ss"w=rd\nline2\'x'


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(secrets.shutil, "which", lambda _: None)
    return tmp_path


class Keychain:
    """Stub subprocess keychain; records argv + stdin."""

    def __init__(self, fail=False):
        self.store, self.calls, self.fail = {}, [], fail

    def __call__(self, argv, stdin=None):
        self.calls.append((argv, stdin))
        if self.fail:
            return subprocess.CompletedProcess(argv, 1, "", "boom")
        svc = next((argv[i + 1] for i, a in enumerate(argv) if a == "-s"), None) or argv[-1]
        if argv[0] == "security" and argv[1] == "-i":
            parts = stdin.split()
            self.store[parts[parts.index("-s") + 1]] = parts[-1]
            return subprocess.CompletedProcess(argv, 0, "", "")
        if "store" in argv:
            self.store[svc] = stdin
        elif "find-generic-password" in argv or "lookup" in argv:
            if svc not in self.store:
                return subprocess.CompletedProcess(argv, 1, "", "nf")
            return subprocess.CompletedProcess(argv, 0, self.store[svc] + "\n", "")
        else:
            self.store.pop(svc, None)
        return subprocess.CompletedProcess(argv, 0, "", "")


@pytest.fixture
def kc(home, monkeypatch):
    k = Keychain()
    monkeypatch.setattr(secrets.shutil, "which", lambda n: "/bin/" + n)
    monkeypatch.setattr(secrets, "_run", k)
    return k


def test_roundtrip_file(home):  # AC1
    secrets.set("google", "learnn", VAL)
    assert secrets.get("google", "learnn") == VAL
    secrets.delete("google", "learnn")
    with pytest.raises(ConnectorError) as e:
        secrets.get("google", "learnn")
    assert e.value.code == "not-found"


def test_roundtrip_keychain(kc):  # AC1, AC2
    secrets.set("google", "learnn", VAL)
    assert secrets.get("google", "learnn") == VAL
    secrets.delete("google", "learnn")
    with pytest.raises(ConnectorError) as e:
        secrets.get("google", "learnn")
    assert e.value.code == "not-found"


def test_keychain_used_no_file(kc, home):  # AC2
    secrets.set("google", "learnn", "v")
    assert "gilberto/google/learnn" in kc.store
    assert not (home / ".config").exists()


def test_value_never_in_argv(kc):  # AC2, AC7
    secrets.set("google", "learnn", VAL)
    secrets.get("google", "learnn")
    secrets.delete("google", "learnn")
    for argv, _ in kc.calls:
        assert not any(VAL in a or VAL.encode().hex() in a for a in argv)


def test_fallback_file_modes(home):  # AC3
    secrets.set("google", "learnn", "v")
    f = home / ".config/gilberto/secrets/google/learnn.env"
    assert stat.S_IMODE(f.stat().st_mode) == 0o600
    assert stat.S_IMODE(f.parent.stat().st_mode) == 0o700


def test_keychain_failure_falls_back(home, monkeypatch):  # AC3
    monkeypatch.setattr(secrets.shutil, "which", lambda n: "/bin/" + n)
    monkeypatch.setattr(secrets, "_run", Keychain(fail=True))
    secrets.set("google", "learnn", "v")
    assert secrets.get("google", "learnn") == "v"


def test_keychain_exception_falls_back(home, monkeypatch):  # AC3
    def boom(*a, **k):
        raise OSError("locked")

    monkeypatch.setattr(secrets.shutil, "which", lambda n: "/bin/" + n)
    monkeypatch.setattr(secrets, "_run", boom)
    secrets.set("google", "learnn", "v")
    assert secrets.get("google", "learnn") == "v"


def test_loose_perm_refused(home):  # AC4
    secrets.set("google", "learnn", "topsecret")
    f = home / ".config/gilberto/secrets/google/learnn.env"
    f.chmod(0o644)
    with pytest.raises(ConnectorError) as e:
        secrets.get("google", "learnn")
    assert e.value.code == "auth"
    assert str(f) in e.value.extra["path"] and "chmod 600" in e.value.extra["fix"]
    assert "topsecret" not in repr(e.value.as_dict())


def test_ref_parse_and_resolve(home):  # AC5
    assert secrets.parse_ref("keychain:gilberto/google/learnn") == ("google", "learnn")
    secrets.set("google", "learnn", "v")
    assert secrets.resolve("keychain:gilberto/google/learnn") == "v"


@pytest.mark.parametrize("ref", ["file:/x", "keychain:other/g/p", "keychain:gilberto/g", "keychain:gilberto/g/p/x", "keychain:gilberto/../p", "keychain:gilberto/G/p", None])
def test_ref_rejects_malformed(ref):  # AC5
    with pytest.raises(ConnectorError):
        secrets.parse_ref(ref)


def test_profile_isolation(home):  # AC6
    secrets.set("google", "learnn", "a")
    secrets.set("google", "personal", "b")
    assert (secrets.get("google", "learnn"), secrets.get("google", "personal")) == ("a", "b")
    secrets.delete("google", "learnn")
    assert secrets.get("google", "personal") == "b"
    with pytest.raises(ConnectorError):
        secrets.get("google", "learnn")


def test_profile_isolation_keychain(kc):  # AC6
    secrets.set("google", "learnn", "a")
    secrets.set("google", "personal", "b")
    assert (secrets.get("google", "learnn"), secrets.get("google", "personal")) == ("a", "b")
    secrets.delete("google", "learnn")
    assert secrets.get("google", "personal") == "b"


def test_never_logged(home, capsys, caplog):  # AC7
    caplog.set_level(logging.DEBUG)
    secrets.set("google", "learnn", "SUPERSECRET")
    secrets.get("google", "learnn")
    (home / ".config/gilberto/secrets/google/learnn.env").chmod(0o666)
    with pytest.raises(ConnectorError) as e:
        secrets.get("google", "learnn")
    with pytest.raises(ConnectorError) as e2:
        secrets.get("google", "nope")
    out = capsys.readouterr()
    blob = out.out + out.err + caplog.text + repr(e.value.as_dict()) + str(e.value) + repr(e2.value.as_dict())
    assert "SUPERSECRET" not in blob


@pytest.mark.parametrize("p,pr", [("../x", "a"), ("a", "../b"), ("a/b", "c"), ("", "a"), ("A", "a"), ("a", "-b"), (None, "a"), ("a", "b.c")])
def test_invalid_segments(home, p, pr):
    for fn in (lambda: secrets.set(p, pr, "v"), lambda: secrets.get(p, pr), lambda: secrets.delete(p, pr)):
        with pytest.raises(ConnectorError):
            fn()
    assert not (home / ".config").exists()


@pytest.mark.parametrize("v", ["", None, 5])
def test_empty_value_rejected(home, v):
    with pytest.raises(ConnectorError):
        secrets.set("google", "learnn", v)


def test_delete_absent_idempotent(home):
    secrets.delete("google", "learnn")
    secrets.delete("google", "learnn")


def test_keychain_read_before_file(kc, home):  # read order
    secrets.set("google", "learnn", "file")  # via keychain
    kc.store["gilberto/google/learnn"] = "kc".encode().hex()
    assert secrets.get("google", "learnn") == "kc"


def test_file_read_when_keychain_misses(kc, home):
    secrets._write_file(secrets._path("google", "learnn"), "fromfile")
    assert secrets.get("google", "learnn") == "fromfile"


def test_default_profile_and_platform_absent(home, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    secrets.set("google", "default", "v")
    assert secrets.get("google", "default") == "v"
