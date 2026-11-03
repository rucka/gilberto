import json
import re
from pathlib import Path

import pytest

from _lib import frontmatter
from rss_helpers import URL, Resp, fixture, http_error

NAME = re.compile(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+-[0-9a-f]{8}\.md")


def out_dir(root):
    return Path(root) / "_ingest" / "intelligence"


def files(root):
    return sorted(p for p in out_dir(root).glob("*.md"))


def test_new_items_one_file_each_with_frontmatter(run, root):  # AC1
    code, out, _ = run(f"--url={URL}")
    assert code == 0 and len(out["items"]) == 2
    fs = files(root)
    assert len(fs) == 2 and all(NAME.fullmatch(p.name) for p in fs)
    p = next(p for p in fs if "first-post" in p.name)
    assert p.name.startswith("2026-11-02-first-post-")
    fm, body = frontmatter.parse(p.read_text())
    assert fm["type"] == "intelligence-source" and fm["source"] == "https://example.com/1" and fm["created"] == "2026-11-02"
    assert "source_profile" not in fm
    assert "Hello [link](https://x.example/a)" in body and "<p>" not in body and "world" in body


def test_source_profile_when_set(run, root):  # AC1
    run(f"--url={URL}", "--profile=rss:default")
    assert all(frontmatter.parse(p.read_text())[0]["source_profile"] == "rss:default" for p in files(root))


def test_bad_profile_is_provider_error(run, root):  # AC1
    code, out, _ = run(f"--url={URL}", "--profile=nope")
    assert code == 1 and out["errors"][0]["code"] == "provider" and not out_dir(root).exists()


def test_filename_deterministic(run, root, tmp_path_factory):  # AC1
    run(f"--url={URL}")
    names = [p.name for p in files(root)]
    other = tmp_path_factory.mktemp("o")
    run(f"--url={URL}", env_root=other)
    assert names == [p.name for p in files(other)]


def test_item_without_title_date_guid(run, root, serve):  # AC1 edge
    serve(Resp(fixture("bare.xml")))
    code, out, _ = run(f"--url={URL}")
    assert code == 0
    (p,) = files(root)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}-example-com-no-title-[0-9a-f]{8}\.md", p.name)


def test_rerun_writes_only_new(run, root, serve):  # AC2
    run(f"--url={URL}")
    before = {p.name: p.read_bytes() for p in files(root)}
    code, out, _ = run(f"--url={URL}")
    assert code == 0 and out["items"] == []
    assert {p.name: p.read_bytes() for p in files(root)} == before
    serve(Resp(fixture("feed.xml").replace(b"</channel>", b"<item><title>Third</title><guid>g-3</guid><link>https://example.com/3</link></item></channel>")))
    code, out, _ = run(f"--url={URL}")
    assert len(out["items"]) == 1 and len(files(root)) == 3


def test_state_records_fetched_ids(run, root):  # AC2
    run(f"--url={URL}")
    state = json.loads((out_dir(root) / ".fetch-rss" / "_state.json").read_text())
    assert sorted(state[URL]["fetched"]) == ["g-1", "g-2"]


def test_corrupt_state_treated_empty(run, root):  # AC2 edge
    (out_dir(root) / ".fetch-rss").mkdir(parents=True)
    (out_dir(root) / ".fetch-rss" / "_state.json").write_text("{not json")
    code, out, err = run(f"--url={URL}")
    assert code == 0 and len(out["items"]) == 2 and "state" in err


def test_never_overwrites_existing_file(run, root):  # business rule
    run(f"--url={URL}")
    p = files(root)[0]
    p.write_text("edited")
    (out_dir(root) / ".fetch-rss" / "_state.json").unlink()
    run(f"--url={URL}")
    assert p.read_text() == "edited"


def test_write_failure_leaves_state_and_no_partial_files(mod, run, root, monkeypatch):  # AC2
    real = mod.Transaction.write
    n = []

    def flaky(self, path, data):
        if n:
            raise OSError("disk")
        n.append(1)
        real(self, path, data)

    monkeypatch.setattr(mod.Transaction, "write", flaky)
    code, out, _ = run(f"--url={URL}")
    assert code == 1 and out["errors"][0]["code"] == "provider"
    assert files(root) == [] and not (out_dir(root) / ".fetch-rss" / "_state.json").exists()


@pytest.mark.parametrize("status,code", [(404, "not-found"), (429, "rate-limit"), (500, "provider")])
def test_http_errors_typed_no_state(run, root, serve, status, code):  # AC3
    serve(http_error(status))
    rc, out, _ = run(f"--url={URL}")
    assert rc == 1 and out["errors"][0]["code"] == code
    assert not out_dir(root).exists()


def test_rate_limit_retries_with_backoff_then_succeeds(mod, run, root, serve):  # AC3
    sleeps = []
    mod._sleep = sleeps.append
    calls = serve(http_error(429), http_error(429), Resp(fixture("feed.xml")))
    code, out, _ = run(f"--url={URL}")
    assert code == 0 and len(calls) == 3 and sleeps == [0.5, 1.0] and len(files(root)) == 2


def test_network_error_retried_then_provider(mod, run, serve):  # AC3
    calls = serve(OSError("down"))
    code, out, _ = run(f"--url={URL}")
    assert code == 1 and out["errors"][0]["code"] == "provider" and len(calls) == 3


def test_malformed_no_entries_is_provider(run, root, serve):  # AC3 edge
    serve(Resp(b"<html>not a feed <b>"))
    code, out, _ = run(f"--url={URL}")
    assert code == 1 and out["errors"][0]["code"] == "provider" and not out_dir(root).exists()


def test_malformed_with_entries_proceeds(run, root, serve):  # AC3 edge
    serve(Resp(fixture("feed.xml").replace(b"</channel></rss>", b"</channel>")))
    code, out, _ = run(f"--url={URL}")
    assert code == 0 and len(files(root)) == 2


@pytest.mark.parametrize("url", ["not a url", "ftp://x.example/f", "https://u:p@x.example/f", ""])
def test_invalid_url_nothing_written(mod, run, root, serve, url):  # AC4
    calls = serve(Resp(fixture("feed.xml")))
    code, out, _ = run(f"--url={url}")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_URL"
    assert calls == [] and list(Path(root).iterdir()) == []


def test_missing_url_arg(run):  # AC4
    code, out, _ = run()
    assert code == 1 and out["errors"][0]["code"] == "INVALID_ARGS"


def test_ingest_scan_accepts_output_unchanged(run, root):  # AC5
    import importlib.util

    run(f"--url={URL}")
    spec = importlib.util.spec_from_file_location("ing", Path(__file__).resolve().parents[2] / "gilberto-process-ingest" / "script.py")
    ing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ing)
    before = {p.name: p.read_bytes() for p in files(root)}
    assert ing._scan(str(out_dir(root)), 0) == sorted(before)
    assert {p.name: p.read_bytes() for p in files(root)} == before
    assert Path(next(iter(before))).suffix in ing.SUPPORTED
