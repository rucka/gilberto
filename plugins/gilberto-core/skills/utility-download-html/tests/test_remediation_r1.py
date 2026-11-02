import http.client
import importlib.util
import json
import re

import pytest

from dl_helpers import ARTICLE, SCRIPT, Resp, err_code

SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
PARA = "La città è più bella quando il caffè è caldo e la perché è chiara. " * 6


def _latin1_page(meta=True):
    head = '<meta charset="iso-8859-1">' if meta else ""
    html = (
        f"<!doctype html><html><head>{head}<title>La città è più bella</title></head><body>"
        f"<article><h1>La città è più bella</h1><p>{PARA}</p><p>{PARA}</p><p>{PARA}</p></article></body></html>"
    )
    return html.encode("latin-1")


def _written_text(root, out):
    assert out["written"], out
    return (root / out["written"][0]).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "body,ctype",
    [
        (_latin1_page(meta=True), "text/html; charset=iso-8859-1"),
        (_latin1_page(meta=False), "text/html; charset=iso-8859-1"),
        (_latin1_page(meta=True), "text/html"),
    ],
    ids=["header+meta", "header-only", "meta-only"],
)
def test_latin1_charset_preserved(mod, run, root, body, ctype):
    mod._open = lambda req, timeout: Resp(body=body, ctype=ctype)
    code, out, _ = run("--url=https://blog.example.com/citta")
    assert code == 0 and out["status"] == "ok"
    text = _written_text(root, out)
    assert "città" in text and "\ufffd" not in text
    assert "\ufffd" not in out["written"][0]
    assert "citt-" not in out["written"][0]


@pytest.fixture
def real_mod():
    spec = importlib.util.spec_from_file_location("utility_download_html_real", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m._open = lambda req, timeout: (_ for _ in ()).throw(AssertionError("network touched"))
    return m


@pytest.mark.parametrize(
    "url",
    ["https://a..b.com/x", "https://" + "a" * 64 + ".com/x", "https://.example.com/x"],
    ids=["empty-label", "label-64", "leading-dot"],
)
def test_bad_host_label_is_json_error(real_mod, root, capsys, url):
    code = real_mod.main([f"--url={url}"], {"GILBERTO_ROOT": str(root)})
    out = json.loads(capsys.readouterr().out)
    assert code == 1 and out["status"] == "error" and err_code(out) == "INVALID_URL"
    assert list((root / "_ingest").iterdir()) == []


@pytest.mark.parametrize("bad", ["https://a..b.com/x", "https://" + "a" * 64 + ".com/x"], ids=["empty-label", "label-64"])
def test_bad_host_label_on_redirect_is_json_error(mod, run, root, bad):
    spec = importlib.util.spec_from_file_location("utility_download_html_real2", SCRIPT)
    real = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(real)
    mod._resolve = lambda host: ["93.184.216.34"] if host == "blog.example.com" else real._resolve(host)

    def op(req, timeout):
        mod._SafeRedirect().redirect_request(req, None, 302, "Found", {}, bad)
        raise AssertionError("redirect to bad host followed")

    mod._open = op
    code, out, _ = run("--url=https://blog.example.com/x")
    assert code == 1 and out["status"] == "error" and err_code(out) in ("INVALID_URL", "FETCH_FAILED"), out
    assert list((root / "_ingest").iterdir()) == []


@pytest.mark.parametrize(
    "exc",
    [http.client.BadStatusLine("x"), http.client.IncompleteRead(b"ab")],
    ids=["BadStatusLine", "IncompleteRead"],
)
def test_http_client_exception_is_fetch_failed(mod, run, root, exc):
    def op(req, timeout):
        raise exc

    mod._open = op
    code, out, _ = run("--url=https://blog.example.com/x")
    assert code == 1 and err_code(out) == "FETCH_FAILED"
    assert list((root / "_ingest").iterdir()) == []


def test_incomplete_read_at_body_read_is_fetch_failed(mod, run, root):
    class Trunc(Resp):
        def read(self, n=-1):
            raise http.client.IncompleteRead(b"ab", 10)

    mod._open = lambda req, timeout: Trunc()
    code, out, _ = run("--url=https://blog.example.com/x")
    assert code == 1 and out["status"] == "error" and err_code(out) == "FETCH_FAILED", out
    assert list((root / "_ingest").iterdir()) == []


def _long_title_open(mod):
    mod._open = lambda req, timeout: Resp(body=ARTICLE.replace(b"The Quiet Power of Slow Mornings", b"x" * 70))


def _stem(rel):
    return rel.rsplit("/", 1)[1][: -len(".md")]


def test_slug_collision_stays_within_slug_rule(mod, run, root):
    _long_title_open(mod)
    names = []
    for i in range(12):
        code, out, _ = run(f"--url=https://site{i}.example.org/p")
        assert code == 0 and out["status"] == "ok", out
        names.append(out["written"][0])
    stems = [_stem(n) for n in names]
    assert len(set(stems)) == 12
    for s in stems:
        assert SLUG_RE.fullmatch(s), s
