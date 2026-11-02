from dl_helpers import Resp
import pytest
from test_remediation_r1 import _latin1_page, _long_title_open, _written_text


def _utf8_body():
    return _latin1_page(meta=True).decode("latin-1").replace("iso-8859-1", "utf-8").encode("utf-8")


def test_utf8_accents_control(mod, run, root):
    mod._open = lambda req, timeout: Resp(body=_utf8_body(), ctype="text/html; charset=utf-8")
    code, out, _ = run("--url=https://blog.example.com/citta")
    text = _written_text(root, out)
    assert code == 0 and "città" in text and "\ufffd" not in text


def test_unknown_charset_label_control(mod, run, root):
    mod._open = lambda req, timeout: Resp(body=_utf8_body(), ctype="text/html; charset=bogus-9")
    code, out, _ = run("--url=https://blog.example.com/citta")
    assert code == 0 and out["status"] == "ok", out
    text = _written_text(root, out)
    assert "città" in text and "\ufffd" not in text


def test_header_wins_over_meta_control(mod, run, root):
    body = _latin1_page(meta=True).decode("latin-1").encode("utf-8")
    mod._open = lambda req, timeout: Resp(body=body, ctype="text/html; charset=utf-8")
    code, out, _ = run("--url=https://blog.example.com/citta")
    text = _written_text(root, out)
    assert code == 0 and "città" in text and "\ufffd" not in text


@pytest.mark.parametrize("idx", [1, 10], ids=["url-2", "url-11"])
def test_long_title_rerun_is_idempotent(mod, run, root, idx):
    _long_title_open(mod)
    names = []
    for i in range(12):
        code, out, _ = run(f"--url=https://site{i}.example.org/p")
        assert code == 0 and out["status"] == "ok", out
        names.append(out["written"][0])
    before = sorted(p.name for p in (root / "_ingest").iterdir())
    code, out, _ = run(f"--url=https://site{idx}.example.org/p")
    assert code == 0 and out["written"] == [] and out["skipped"] == [names[idx]], out
    assert sorted(p.name for p in (root / "_ingest").iterdir()) == before
