import json
import os

import pytest

from _lib import atomic_write, frontmatter, result
from _lib.result import MechanicError


def test_atomic_write_ok(tmp_path):
    p = tmp_path / "f.md"
    atomic_write.atomic_write(str(p), "x")
    assert p.read_text() == "x"
    assert os.listdir(tmp_path) == ["f.md"]


@pytest.mark.parametrize("exc", [OSError(5, "EIO"), KeyboardInterrupt()])
def test_atomic_write_failure_leaves_no_tmp(tmp_path, monkeypatch, exc):
    def boom(*_):
        raise exc

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(type(exc)):
        atomic_write.atomic_write(str(tmp_path / "f.md"), "x")
    assert os.listdir(tmp_path) == []


def test_transaction_commit_and_rollback(tmp_path, monkeypatch):
    with atomic_write.Transaction() as t:
        t.mkdir(str(tmp_path / "a" / "b"))
        t.write(str(tmp_path / "a" / "b" / "f"), "1")
    assert (tmp_path / "a" / "b" / "f").read_text() == "1"

    (tmp_path / "keep").mkdir()
    (tmp_path / "keep" / "old").write_text("o")
    with pytest.raises(OSError):
        with atomic_write.Transaction() as t:
            t.mkdir(str(tmp_path / "n" / "m"))
            t.write(str(tmp_path / "n" / "m" / "f"), "1")
            t.write(str(tmp_path / "keep" / "old"), "overwritten")  # pre-existing: not removed on rollback
            raise OSError("late")
    assert not (tmp_path / "n").exists()
    assert (tmp_path / "keep" / "old").exists()


def test_frontmatter_roundtrip():
    fm, body = frontmatter.parse('---\ntype: x-y\ntopics: [a, "b"]\nn: 3\nq: \'s\'\nr: raw text\n---\nbody\n')
    assert fm == {"type": "x-y", "topics": ["a", "b"], "n": 3, "q": "s", "r": "raw text"}
    assert body == "body\n"
    assert frontmatter.parse("no fm") == ({}, "no fm")
    assert frontmatter.parse(frontmatter.dump(fm, body)) == (fm, body)


def test_set_key():
    t = "---\ntype: a\nupdated: '1'\n---\nbody [[x]]\n"
    assert frontmatter.set_key(t, "updated", "2") == '---\ntype: a\nupdated: "2"\n---\nbody [[x]]\n'
    assert frontmatter.set_key(t, "new", "v").count("new: \"v\"") == 1
    assert frontmatter.set_key("plain", "k", "v") == '---\nk: "v"\n---\nplain'


def test_result_run(capsys):
    def ok(argv, env):
        return ["a"], []

    def skipped(argv, env):
        return [], ["a"]

    def bad(argv, env):
        raise MechanicError("INVALID_SLUG", input="X")

    assert result.run(ok, [], {}) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
    assert result.run(skipped, [], {}) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "skipped"
    assert result.run(bad, [], {}) == 1
    out = capsys.readouterr()
    assert json.loads(out.out) == {
        "status": "error", "written": [], "skipped": [], "errors": [{"code": "INVALID_SLUG", "input": "X"}]
    }
    assert "INVALID_SLUG" in out.err
