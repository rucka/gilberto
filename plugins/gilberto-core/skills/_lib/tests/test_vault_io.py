import os

import pytest

from _lib import vault_io
from _lib.result import MechanicError


def test_root(vault, tmp_path):
    assert vault_io.vault_root({"GILBERTO_ROOT": str(vault)}) == os.path.realpath(vault)
    for env in ({}, {"GILBERTO_ROOT": str(tmp_path / "nope")}):
        with pytest.raises(MechanicError) as e:
            vault_io.vault_root(env)
        assert e.value.code == "INVALID_PATH"


def test_resolve_contained(vault):
    root = os.path.realpath(vault)
    assert vault_io.resolve(root, "projects/x.md") == os.path.join(root, "projects", "x.md")
    assert vault_io.resolve(root, ".") == root


def test_resolve_escape_and_symlink(vault, tmp_path):
    root = os.path.realpath(vault)
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, vault / "projects" / "evil")
    for rel in ("../outside", "projects/evil/x.md"):
        with pytest.raises(MechanicError) as e:
            vault_io.resolve(root, rel)
        assert e.value.as_dict() == {"code": "INVALID_PATH", "input": rel}
