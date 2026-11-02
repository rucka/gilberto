import datetime
import importlib.util
import io
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from dl_helpers import ARTICLE, CHROME, HERE, URL, Resp, err_code  # noqa: E402,F401

trafilatura = pytest.importorskip("trafilatura")


def test_ac1_main_content_only(run, root):
    code, out, _ = run(f"--url={URL}")
    assert code == 0 and out["status"] == "ok" and out["errors"] == []
    assert out["written"] == ["_ingest/the-quiet-power-of-slow-mornings.md"]
    text = (root / out["written"][0]).read_text()
    assert "Starting the day without a screen" in text and "Attention is a limited resource" in text
    for chrome in CHROME:
        assert chrome not in text
    assert not list(root.rglob("*.tmp.*"))


def test_ac2_frontmatter_keys(run, root):
    _, out, _ = run(f"--url={URL}")
    from _lib import frontmatter

    fm, body = frontmatter.parse((root / out["written"][0]).read_text())
    today = datetime.date.today().isoformat()
    assert list(fm) == ["type", "topics", "source", "title", "created", "updated"]
    assert fm["type"] == "intelligence-source" and fm["topics"] == []
    assert fm["source"] == URL and fm["title"] == "The Quiet Power of Slow Mornings"
    assert fm["created"] == fm["updated"] == today
    assert body.strip()


def test_ac3_idempotent_and_force(mod, run, root):
    _, first, _ = run(f"--url={URL}")
    path = root / first["written"][0]
    path.write_text(path.read_text() + "\nlocal edit\n")
    before = path.read_bytes()
    code, out, err = run(f"--url={URL}")
    assert code == 0 and out["status"] == "skipped" and out["written"] == []
    assert out["skipped"] == first["written"] and "skipped (idempotent)" in err
    assert path.read_bytes() == before
    code, out, _ = run(f"--url={URL}", "--force")
    assert code == 0 and out["status"] == "ok" and out["written"] == first["written"]
    assert b"local edit" not in path.read_bytes()
    assert len(list((root / "_ingest").iterdir())) == 1


def test_force_keeps_created(run, root):
    _, out, _ = run(f"--url={URL}")
    path = root / out["written"][0]
    path.write_text(path.read_text().replace(datetime.date.today().isoformat(), "2020-01-01", 1))
    run(f"--url={URL}", "--force")
    assert 'created: "2020-01-01"' in path.read_text()


def test_slug_collision_numeric_suffix(run, root):
    _, a, _ = run(f"--url={URL}")
    _, b, _ = run("--url=https://other.example.org/same-title")
    assert a["written"] == ["_ingest/the-quiet-power-of-slow-mornings.md"]
    assert b["written"] == ["_ingest/the-quiet-power-of-slow-mornings-2.md"]
    _, again, _ = run("--url=https://other.example.org/same-title")
    assert again["status"] == "skipped" and again["skipped"] == b["written"]


def test_no_content(mod, run, root):
    mod._open = lambda req, timeout: Resp(body=b"<html><head><title>t</title></head><body></body></html>")
    code, out, _ = run(f"--url={URL}")
    assert code == 1 and err_code(out) == "NO_CONTENT"
    assert list((root / "_ingest").iterdir()) == []


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Café Society: A Début!", "cafe-society-a-debut"),
        ("  --Hello   World--  ", "hello-world"),
        ("x" * 100, "x" * 64),
        ("", "blog-example-com-posts-slow-mornings"),
        ("!!!", "blog-example-com-posts-slow-mornings"),
    ],
)
def test_slug_rules(mod, title, expected):
    s = mod._slug(title, URL)
    assert s == expected and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", s)


def test_ac4_json_on_stdout_prose_on_stderr(run):
    _, out, err = run(f"--url={URL}")
    assert set(out) == {"status", "written", "skipped", "errors"}
    assert err == "" or not err.lstrip().startswith("{")
