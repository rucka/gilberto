import calendar
import hashlib
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import connector, frontmatter, result, vault_io  # noqa: E402
from _lib.atomic_write import Transaction  # noqa: E402
from _lib.connector import ConnectorError  # noqa: E402
from _lib.result import MechanicError  # noqa: E402
from _lib.url_validate import validate_url  # noqa: E402

TIMEOUT = 15
MAX_BYTES = 10_000_000
OUT = "_ingest/intelligence"
STATE = ".fetch-rss/_state.json"
_sleep = time.sleep


def _open(req, timeout):
    return urllib.request.urlopen(req, timeout=timeout)


def _fetch_once(url):
    req = urllib.request.Request(url, headers={"User-Agent": "gilberto-utility-fetch-rss", "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    try:
        with _open(req, TIMEOUT) as r:
            return r.read(MAX_BYTES)
    except urllib.error.HTTPError as e:
        if e.code == 404 or e.code == 410:
            raise ConnectorError("not-found", status=e.code)
        if e.code == 429:
            raise ConnectorError("rate-limit", status=e.code)
        raise OSError(f"http {e.code}")


def fetch(url):
    return connector.retry(lambda: _fetch_once(url), sleep=lambda s: _sleep(s))


def _parse_feed(raw):
    import feedparser

    d = feedparser.parse(raw)
    if d.bozo and not d.entries:
        raise ConnectorError("provider", reason=f"malformed feed: {d.bozo_exception}")
    return d.entries


def _slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48].strip("-")


def _md(markup):
    s = re.sub(r"<a\b[^>]*?href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", r"[\2](\1)", markup or "", flags=re.S | re.I)
    s = re.sub(r"<(br\s*/?|/p|/div|/li|/h[1-6])>", "\n", s, flags=re.I)
    s = html.unescape(re.sub(r"<(?!/?$)[^>]*>", "", s))
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def _item(e, feed_url):
    link = e.get("link") or ""
    key = e.get("id") or link or hashlib.sha1(f"{e.get('title', '')}{e.get('summary', '')}".encode()).hexdigest()
    t = e.get("published_parsed") or e.get("updated_parsed")
    date = time.strftime("%Y-%m-%d", time.gmtime(calendar.timegm(t))) if t else time.strftime("%Y-%m-%d")
    title = (e.get("title") or "").strip()
    slug = _slug(title) or _slug(re.sub(r"^https?://", "", link)) or "item"
    content = (e.get("content") or [{}])[0].get("value") or e.get("summary") or ""
    body = (f"# {title}\n\n" if title else "") + _md(content) + (f"\n\n[Source]({link})" if link else "") + "\n"
    return {"id": key, "name": f"{date}-{slug}-{hashlib.sha1(key.encode()).hexdigest()[:8]}.md", "date": date, "title": title, "source": link or feed_url, "body": body}


def _markdown(it, profile):
    fm = {"title": it["title"]} if it["title"] else {}
    md = frontmatter.dump(fm, it["body"])
    if profile:
        return connector.normalize_item(md, it["source"], profile, created=it["date"])
    return frontmatter.dump({**fm, "type": connector.TYPE, "source": it["source"], "created": it["date"]}, it["body"])


def _state(path):
    state = connector.load_state(path)
    if not state and os.path.exists(path):
        result.log(f"state unreadable or corrupt, treated as empty: {path}")
    return state


def _parse(argv):
    p = result.ArgParser(prog="utility-fetch-rss")
    p.add_argument("--url", required=True)
    p.add_argument("--profile")
    return p.parse_args(argv)


def _run(argv, env):
    a = _parse(argv)
    validate_url(a.url)
    root = vault_io.vault_root(env)
    out = vault_io.resolve(root, OUT)
    state_path = os.path.join(out, STATE)
    entries = _parse_feed(fetch(a.url))
    state = _state(state_path)
    fresh = connector.new_items(state, a.url, [_item(e, a.url) for e in entries])
    with Transaction() as tx:
        tx.mkdir(os.path.dirname(state_path))
        for it in fresh:
            path = os.path.join(out, it["name"])
            if not os.path.exists(path):
                tx.write(path, _markdown(it, a.profile))
        connector.save_state(state_path, state)
    return [{"id": it["id"], "path": f"{OUT}/{it['name']}"} for it in fresh]


def main(argv=None, env=None):
    try:
        return connector.run_utility(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)
    except MechanicError as e:
        result.log(f"error: {e.code}")
        print(json.dumps({"errors": [e.as_dict()]}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
