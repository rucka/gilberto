import re
from urllib.parse import urlsplit, urlunsplit

from .result import MechanicError

_BAD_CHARS = re.compile(r"[\s\\<>\"{}|^`\x00-\x1f\x7f]")
_HOST = re.compile(r"[A-Za-z0-9._~-]+|[0-9A-Fa-f:.]+")


def validate_url(raw):
    """Syntactic check: absolute http/https URL with host, no credentials, whitespace or `..` segments."""

    def bad(reason):
        return MechanicError("INVALID_URL", input=raw, reason=reason)

    if not isinstance(raw, str) or not raw or _BAD_CHARS.search(raw):
        raise bad("empty, non-string or forbidden characters")
    try:
        u = urlsplit(raw)
        u.port
    except ValueError:
        raise bad("malformed")
    if u.scheme.lower() not in ("http", "https"):
        raise bad("scheme must be http or https")
    if not raw[len(u.scheme):].startswith("://") or not u.hostname or not _HOST.fullmatch(u.hostname):
        raise bad("missing or invalid host")
    if "@" in u.netloc:
        raise bad("credentials not allowed")
    if ".." in u.path.split("/"):
        raise bad("path traversal")
    return raw


def normalize_url(raw):
    """Lowercase scheme and host; a lone `/` path is stripped (`https://a.com/` == `https://a.com`)."""
    validate_url(raw)
    u = urlsplit(raw)
    return urlunsplit((u.scheme.lower(), u.netloc.lower(), "" if u.path == "/" else u.path, u.query, u.fragment))
