import pytest

from _lib.result import MechanicError
from _lib.url_validate import normalize_url, validate_url

VALID = [
    "https://example.com/feed.xml",
    "http://example.com",
    "HTTPS://Example.COM:8080/a?b=c#d",
    "https://[::1]/x",
]
INVALID = [
    "file:///etc/passwd",
    "javascript:alert(1)",
    "ftp://example.com/x",
    "example.com/feed",
    "/relative/path",
    "https://",
    "https:example.com",
    "https:///path",
    "https://exa mple.com",
    "https://example.com/a b",
    "https://example.com/../etc",
    "https://example.com\\..\\x",
    "https://user:pw@example.com",
    "https://example.com:notaport",
    "https://exämple.com",
    "",
    None,
    42,
]


@pytest.mark.parametrize("url", VALID)
def test_valid(url):
    assert validate_url(url) == url


@pytest.mark.parametrize("url", INVALID)
def test_invalid(url):
    with pytest.raises(MechanicError) as e:
        validate_url(url)
    assert e.value.code == "INVALID_URL" and e.value.extra["input"] == url


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("HTTPS://Example.COM/Feed.xml", "https://example.com/Feed.xml"),
        ("https://example.com/", "https://example.com"),
        ("https://example.com", "https://example.com"),
        ("https://example.com/a/", "https://example.com/a/"),
        ("https://Example.com/?q=1", "https://example.com?q=1"),
    ],
)
def test_normalize(raw, expected):
    assert normalize_url(raw) == expected


def test_normalize_rejects_invalid():
    with pytest.raises(MechanicError):
        normalize_url("file:///x")
