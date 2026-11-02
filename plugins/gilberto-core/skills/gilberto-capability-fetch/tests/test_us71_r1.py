import json
import subprocess
import sys
from pathlib import Path

import pytest

FORGE = Path(__file__).resolve().parents[2] / "mechanic-forge-source" / "script.py"
ITEM = {"id": "1", "markdown": "---\ntype: article\n---\n\nbody\n"}


def forge(root, url):
    (root / "anatomy").mkdir(parents=True, exist_ok=True)
    (root / "intelligence").mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, str(FORGE), "--type=rss", f"--url={url}", "--cadence=daily", "--target-pillar=intelligence", "--target-topic=ai-news"]
    p = subprocess.run(argv, env={"GILBERTO_ROOT": str(root), "PATH": ""}, capture_output=True, text=True, timeout=60, check=False)
    assert p.returncode == 0, p.stdout + p.stderr


def integration(root, rel, text):
    f = root / "anatomy/integrations" / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)


def dispatch(fetch, utility, **entry):
    e = {"pillar": "intelligence", "contributor": "core", "url": "https://a.example/f", **entry}
    return fetch.mod.dispatch(str(fetch.root), e, {"GILBERTO_UTILITY_PATH": utility.path})


@pytest.mark.parametrize("url", ["https://example.com/café", "https://example.com/😀"])
def test_us71_r1_forged_nonascii_url_roundtrips(fetch, url):
    forge(fetch.root, url)
    entries, errors = fetch.mod.load_sources(str(fetch.root))
    assert errors == []
    assert [e["url"] for e in entries] == [url]


def test_us71_r1_forged_ascii_url_roundtrips(fetch):
    forge(fetch.root, "https://example.com/feed.xml?a=1")
    entries, _ = fetch.mod.load_sources(str(fetch.root))
    assert entries[0]["url"] == "https://example.com/feed.xml?a=1"


def test_us71_r1_bare_key_stays_raw(fetch, source):
    source("intelligence", "core", "```yaml\nhttps://a.example/x\\u00e9:\n  type: rss\n```\n")
    entries, _ = fetch.mod.load_sources(str(fetch.root))
    assert entries[0]["url"] == "https://a.example/x\\u00e9"


def test_us71_r1_quoted_key_invalid_escape_isolated(fetch, source):
    text = "```yaml\n" + '"https://a.example/ok1":\n  type: rss\n"https://a.example/x\\q":\n  type: rss\n"https://a.example/x\\u00":\n  type: rss\n"https://a.example/ok2":\n  type: rss\n' + "```\n"
    source("intelligence", "core", text)
    entries, errors = fetch.mod.load_sources(str(fetch.root))
    urls = [e["url"] for e in entries]
    assert "https://a.example/ok1" in urls and "https://a.example/ok2" in urls
    assert all(e["code"] == "MALFORMED_ENTRY" for e in errors)
    assert len(urls) + len(errors) == 4


def test_us71_r1_nonascii_url_source_filter_and_mcp_request(fetch, utility):
    url = "https://example.com/café"
    forge(fetch.root, url)
    entries, errors = fetch.mod.load_sources(str(fetch.root), source=url)
    assert errors == [] and [e["url"] for e in entries] == [url]
    kind, req = dispatch(fetch, utility, **{**entries[0], "provider": "slack", "fallback": "mcp"})
    assert kind == "mcp" and req["url"] == url


def test_us71_r1_utility_receives_decoded_url(fetch, utility):
    forge(fetch.root, "https://example.com/café")
    code, _out, _ = fetch("--source=core", env={"GILBERTO_UTILITY_PATH": utility("utility-fetch-rss", [ITEM])})
    assert code == 0
    assert utility.args("utility-fetch-rss") == ["--url=https://example.com/café"]
    state = json.loads((fetch.root / "anatomy/playbooks/intelligence/sources/core/_state.json").read_text())
    assert list(state) == ["https://example.com/café"]


def test_us71_r1_profile_layout_fallback_mcp(fetch, utility):
    integration(fetch.root, "slack/work.md", "---\ntype: integration\nfallback: mcp\n---\n")
    kind, req = dispatch(fetch, utility, provider="slack", profile="work")
    assert kind == "mcp" and req["profile"] == "work"


def test_us71_r1_default_layout_fallback_mcp(fetch, utility):
    integration(fetch.root, "slack/default.md", "---\ntype: integration\nfallback: mcp\n---\n")
    assert dispatch(fetch, utility, provider="slack")[0] == "mcp"


def test_us71_r1_profile_file_wins_over_flat(fetch, utility):
    integration(fetch.root, "slack.md", "---\ntype: integration\nfallback: mcp\n---\n")
    integration(fetch.root, "slack/work.md", "---\ntype: integration\nfallback: none\n---\n")
    assert dispatch(fetch, utility, provider="slack", profile="work")[0] == "manual"


def test_us71_r1_flat_layout_still_honoured(fetch, utility):
    integration(fetch.root, "slack.md", "---\ntype: integration\nfallback: mcp\n---\n")
    assert dispatch(fetch, utility, provider="slack")[0] == "mcp"


def test_us71_r1_profile_falls_back_to_flat(fetch, utility):
    integration(fetch.root, "slack.md", "---\ntype: integration\nfallback: mcp\n---\n")
    assert dispatch(fetch, utility, provider="slack", profile="work")[0] == "mcp"


def test_us71_r1_default_file_wins_over_flat(fetch, utility):
    integration(fetch.root, "slack.md", "---\ntype: integration\nfallback: mcp\n---\n")
    integration(fetch.root, "slack/default.md", "---\ntype: integration\nfallback: none\n---\n")
    assert dispatch(fetch, utility, provider="slack")[0] == "manual"


@pytest.mark.parametrize("profile,rel", [
    ("../../playbooks/intelligence/sources/core", "../playbooks/intelligence/sources/core.md"),
    ("a/b", "slack/a/b.md"),
])
def test_us71_r1_profile_path_component_rejected(fetch, utility, profile, rel):
    integration(fetch.root, rel, "---\ntype: integration\nfallback: mcp\n---\n")
    try:
        kind = dispatch(fetch, utility, provider="slack", profile=profile)[0]
    except fetch.mod.MechanicError:
        kind = "error"
    assert kind != "mcp"


def test_us71_r1_valid_profile_slug_resolves(fetch, utility):
    integration(fetch.root, "slack/acme-2.md", "---\ntype: integration\nfallback: mcp\n---\n")
    kind, req = dispatch(fetch, utility, provider="slack", profile="acme-2")
    assert kind == "mcp" and req["profile"] == "acme-2"
