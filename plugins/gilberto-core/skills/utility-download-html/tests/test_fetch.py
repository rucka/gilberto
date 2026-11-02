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

from dl_helpers import ARTICLE, CHROME, URL, Resp, err_code  # noqa: E402,F401


# --- T-1: fetch, validation, SSRF (no trafilatura needed) ---


@pytest.mark.parametrize("bad", ["ftp://x.com/a", "not a url", "https://u:p@x.com/", "", "https://x.com/../a"])
def test_invalid_url_no_network(mod, run, root, bad):
    def boom(*a, **k):
        raise AssertionError("network touched")

    mod._open = boom
    mod._resolve = boom
    code, out, _ = run(f"--url={bad}")
    assert code == 1 and out["status"] == "error" and err_code(out) == "INVALID_URL"
    assert list((root / "_ingest").iterdir()) == []


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1", "172.16.0.1", "0.0.0.0"])
def test_private_host_rejected(mod, run, root, ip):
    mod._resolve = lambda host: [ip]
    mod._open = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network touched"))
    code, out, _ = run(f"--url={URL}")
    assert code == 1 and err_code(out) == "INVALID_URL"
    assert list((root / "_ingest").iterdir()) == []


def test_mixed_resolution_rejected(mod, run):
    mod._resolve = lambda host: ["93.184.216.34", "10.0.0.1"]
    code, out, _ = run(f"--url={URL}")
    assert code == 1 and err_code(out) == "INVALID_URL"


def test_dns_failure_is_fetch_failed(mod, run):
    def fail(host):
        raise OSError("nxdomain")

    mod._resolve = fail
    code, out, _ = run(f"--url={URL}")
    assert code == 1 and err_code(out) == "FETCH_FAILED"


def test_redirect_to_private_blocked(mod):
    mod._resolve = lambda host: ["10.0.0.1"] if host == "internal.example" else ["93.184.216.34"]
    h = mod._SafeRedirect()
    req = urllib.request.Request(URL)
    with pytest.raises(mod.MechanicError) as e:
        h.redirect_request(req, None, 302, "Found", {}, "http://internal.example/x")
    assert e.value.code == "INVALID_URL"


@pytest.mark.parametrize(
    "exc",
    [
        urllib.error.HTTPError(URL, 404, "nf", {}, io.BytesIO()),
        urllib.error.URLError("refused"),
        TimeoutError("slow"),
    ],
)
def test_fetch_errors(mod, run, root, exc):
    def op(req, timeout):
        raise exc

    mod._open = op
    code, out, _ = run(f"--url={URL}")
    assert code == 1 and err_code(out) == "FETCH_FAILED"
    assert list((root / "_ingest").iterdir()) == []


def test_non_2xx_response_is_fetch_failed(mod, run):
    mod._open = lambda req, timeout: Resp(status=500)
    code, out, _ = run(f"--url={URL}")
    assert code == 1 and err_code(out) == "FETCH_FAILED"


@pytest.mark.parametrize("ctype", ["application/pdf", "image/png", "application/json", ""])
def test_unsupported_content(mod, run, root, ctype):
    mod._open = lambda req, timeout: Resp(ctype=ctype)
    code, out, _ = run(f"--url={URL}")
    assert code == 1 and err_code(out) == "UNSUPPORTED_CONTENT"
    assert list((root / "_ingest").iterdir()) == []


def test_ingest_dir_missing(mod, run, tmp_path):
    (tmp_path / "empty").mkdir()
    code, out, _ = run(f"--url={URL}", env_root=tmp_path / "empty")
    assert code == 1 and err_code(out) == "PATH_NOT_FOUND"


def test_missing_url_arg(run):
    code, out, _ = run()
    assert code == 1 and err_code(out) == "INVALID_ARGS"
