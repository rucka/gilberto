import datetime
import http.client
import ipaddress
import os
import re
import socket
import sys
import unicodedata
import urllib.error
import urllib.request
from urllib.parse import urlsplit

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import frontmatter, result, validate, vault_io  # noqa: E402
from _lib.atomic_write import atomic_write  # noqa: E402
from _lib.result import MechanicError  # noqa: E402
from _lib.url_validate import validate_url  # noqa: E402

TIMEOUT = 15
MAX_BYTES = 5_000_000
HTML_TYPES = ("text/html", "application/xhtml+xml")
TYPE = "intelligence-source"


def _resolve(host):
    return [i[4][0] for i in socket.getaddrinfo(host, None)]


def _open(req, timeout):
    return urllib.request.build_opener(_SafeRedirect).open(req, timeout=timeout)


def _check_host(url):
    """Reject hosts resolving to non-public addresses (any one of them)."""
    host = urlsplit(url).hostname
    try:
        ips = _resolve(host)
    except UnicodeError as e:
        raise MechanicError("INVALID_URL", input=url, reason=f"invalid host: {e}")
    except OSError as e:
        raise MechanicError("FETCH_FAILED", url=url, reason=f"dns: {e}")
    for ip in ips:
        a = ipaddress.ip_address(ip.split("%")[0])
        if not a.is_global or a.is_multicast:
            raise MechanicError("INVALID_URL", input=url, reason=f"non-public address {ip}")


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        _check_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_CHARSET = re.compile(r"charset\s*=\s*[\"']?([A-Za-z0-9_.:-]+)", re.I)


def _decode(raw, header):
    m = _CHARSET.search(header) or _CHARSET.search(raw[:4096].decode("ascii", "ignore"))
    if m:
        try:
            return raw.decode(m.group(1), "replace")
        except LookupError:
            pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def fetch(url):
    validate_url(url)
    _check_host(url)
    req = urllib.request.Request(url, headers={"User-Agent": "gilberto-utility-download-html", "Accept": "text/html"})
    try:
        with _open(req, TIMEOUT) as r:
            status = getattr(r, "status", 200)
            if not 200 <= status < 300:
                raise MechanicError("FETCH_FAILED", url=url, status=status)
            header = r.headers.get("Content-Type") or ""
            ctype = header.split(";")[0].strip().lower()
            if ctype not in HTML_TYPES:
                raise MechanicError("UNSUPPORTED_CONTENT", url=url, contentType=ctype)
            return _decode(r.read(MAX_BYTES), header)
    except urllib.error.HTTPError as e:
        raise MechanicError("FETCH_FAILED", url=url, status=e.code)
    except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
        raise MechanicError("FETCH_FAILED", url=url, reason=str(e))


def _slug(title, url):
    def clean(s):
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:64].strip("-")

    u = urlsplit(url)
    return clean(title or "") or clean(u.hostname + u.path)


def _extract(html, url):
    import trafilatura

    text = html
    body = trafilatura.extract(text, url=url, output_format="markdown", include_comments=False, include_tables=True)
    if not body or not body.strip():
        raise MechanicError("NO_CONTENT", url=url)
    meta = trafilatura.extract_metadata(text, default_url=url)
    return (meta.title if meta and meta.title else ""), body.strip() + "\n"


def _parse(argv):
    p = result.ArgParser(prog="utility-download-html")
    p.add_argument("--url", required=True)
    p.add_argument("--force", action="store_true")
    return p.parse_args(argv)


def _target(ingest, slug, url):
    """-> (path, exists): same-source file for slug (or slug-N), else first free name."""
    n = 1
    while True:
        base = slug if n == 1 else f"{slug[: 64 - len(str(n)) - 1].strip('-')}-{n}"
        path = os.path.join(ingest, f"{base}.md")
        if not os.path.exists(path):
            return path, False
        with open(path, encoding="utf-8") as f:
            if frontmatter.parse(f.read())[0].get("source") == url:
                return path, True
        n += 1


def _run(argv, env):
    a = _parse(argv)
    validate_url(a.url)
    root = vault_io.vault_root(env)
    ingest = os.path.join(root, "_ingest")
    if not os.path.isdir(ingest):
        raise MechanicError("PATH_NOT_FOUND", path="_ingest")
    html = fetch(a.url)
    title, body = _extract(html, a.url)
    slug = _slug(title, a.url)
    validate.slug(slug)
    path, exists = _target(ingest, slug, a.url)
    rel = f"_ingest/{os.path.basename(path)}"
    if exists and not a.force:
        result.log("skipped (idempotent)")
        return [], [rel]
    today = datetime.date.today().isoformat()
    created = today
    if exists:
        with open(path, encoding="utf-8") as f:
            created = frontmatter.parse(f.read())[0].get("created", today)
    fm = {"type": TYPE, "topics": [], "source": a.url, "title": title or slug, "created": created, "updated": today}
    try:
        atomic_write(path, frontmatter.dump(fm, body))
    except OSError as e:
        result.log(f"write failed ({e})")
        raise MechanicError("WRITE_FAILED", error=str(e))
    return [rel], []


def main(argv=None, env=None):
    return result.run(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)


if __name__ == "__main__":
    sys.exit(main())
