import subprocess

import pytest

from _lib import secrets
from _lib.connector import ConnectorError


@pytest.fixture(params=["darwin", "linux"])
def env(request, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(secrets.sys, "platform", request.param)
    monkeypatch.setattr(secrets.shutil, "which", lambda n: "/bin/" + n)
    state = {"store": {}, "dead": True}

    def run(argv, stdin=None):
        if state["dead"]:
            return subprocess.CompletedProcess(argv, 1, "", "")
        if "delete-generic-password" in argv or "clear" in argv:
            return subprocess.CompletedProcess(argv, 1, "", "")
        if "find-generic-password" in argv or "lookup" in argv:
            return subprocess.CompletedProcess(argv, 0, state["store"]["v"] + "\n", "")
        return subprocess.CompletedProcess(argv, 1, "", "")

    monkeypatch.setattr(secrets, "_run", run)
    state["file"] = tmp_path / ".config/gilberto/secrets/google/learnn.env"
    return state


def test_unusable_backend_set_get_delete_get(env):  # r1-4 witness
    secrets.set("google", "learnn", "TOKEN")
    assert env["file"].exists()
    assert secrets.get("google", "learnn") == "TOKEN"
    secrets.delete("google", "learnn")
    assert not env["file"].exists()
    with pytest.raises(ConnectorError) as e:
        secrets.get("google", "learnn")
    assert e.value.code == "not-found"


def test_unusable_backend_delete_absent_idempotent(env):  # r1-4 witness
    secrets.delete("google", "learnn")
    assert not env["file"].exists()


def test_entry_present_delete_failure_raises(env):  # r1-4 control
    env["dead"] = False
    env["store"]["v"] = b"TOKEN".hex()
    with pytest.raises(ConnectorError) as e:
        secrets.delete("google", "learnn")
    assert e.value.code == "provider"


@pytest.fixture(
    params=[
        ("darwin", subprocess.TimeoutExpired(["security"], 15)),
        ("darwin", OSError("blocked")),
        ("linux", subprocess.TimeoutExpired(["secret-tool"], 15)),
        ("linux", OSError("blocked")),
    ],
    ids=["darwin-timeout", "darwin-oserror", "linux-timeout", "linux-oserror"],
)
def raising(request, tmp_path, monkeypatch):
    platform, exc = request.param
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(secrets.sys, "platform", platform)
    monkeypatch.setattr(secrets.shutil, "which", lambda n: "/bin/" + n)
    state = {"store": {}, "dead": True}

    def run(argv, stdin=None):
        if state["dead"] or "delete-generic-password" in argv or "clear" in argv:
            raise exc
        return subprocess.CompletedProcess(argv, 0, state["store"]["v"] + "\n", "")

    monkeypatch.setattr(secrets, "_run", run)
    state["file"] = tmp_path / ".config/gilberto/secrets/google/learnn.env"
    return state


def test_raising_backend_set_get_delete_get(raising):  # r1-4 witness (m-r1-4-w3)
    secrets.set("google", "learnn", "TOKEN")
    assert raising["file"].exists()
    secrets.delete("google", "learnn")
    assert not raising["file"].exists()
    with pytest.raises(ConnectorError) as e:
        secrets.get("google", "learnn")
    assert e.value.code == "not-found"


def test_entry_present_delete_exception_raises(raising):  # r1-4 control (m-r1-4-c2)
    raising["dead"] = False
    raising["store"]["v"] = b"TOKEN".hex()
    with pytest.raises(ConnectorError) as e:
        secrets.delete("google", "learnn")
    assert e.value.code == "provider"
