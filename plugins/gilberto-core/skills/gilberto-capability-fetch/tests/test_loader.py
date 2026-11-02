from fetch_helpers import block


def sources(fetch):
    return fetch.mod.load_sources(str(fetch.root))


def test_loads_every_entry_across_pillars(fetch, source):
    source("intelligence", "core", block("https://a.example/feed", type="rss"), block("https://b.example/feed", type="atom"))
    source("pulse", "oura", block("https://c.example/x", type="oura", provider="oura", profile="me"))
    entries, errors = sources(fetch)
    assert errors == []
    assert [(e["pillar"], e["contributor"], e["url"], e["type"]) for e in entries] == [
        ("intelligence", "core", "https://a.example/feed", "rss"),
        ("intelligence", "core", "https://b.example/feed", "atom"),
        ("pulse", "oura", "https://c.example/x", "oura"),
    ]
    assert entries[2]["provider"] == "oura" and entries[2]["profile"] == "me"


def test_pillar_filter(fetch, source):
    source("intelligence", "core", block("https://a.example/f", type="rss"))
    source("pulse", "core", block("https://b.example/f", type="rss"))
    entries, _ = fetch.mod.load_sources(str(fetch.root), pillar="pulse")
    assert [e["url"] for e in entries] == ["https://b.example/f"]


def test_source_filter_by_contributor_or_url(fetch, source):
    source("intelligence", "core", block("https://a.example/f", type="rss"))
    source("intelligence", "acme", block("https://b.example/f", type="rss"))
    by_name, _ = fetch.mod.load_sources(str(fetch.root), source="acme")
    by_url, _ = fetch.mod.load_sources(str(fetch.root), source="https://a.example/f")
    assert [e["contributor"] for e in by_name] == ["acme"]
    assert [e["url"] for e in by_url] == ["https://a.example/f"]


def test_missing_or_empty_sources_is_noop(fetch):
    assert sources(fetch) == ([], [])
    (fetch.root / "anatomy/playbooks/pulse/sources").mkdir(parents=True)
    assert sources(fetch) == ([], [])


def test_malformed_entry_reported_rest_continue(fetch, source):
    f = source(
        "intelligence",
        "core",
        block("https://ok.example/f", type="rss"),
        block("https://notype.example/f", cadence="daily"),
        "```yaml\n\"https://junk.example/f\":\n  this is not a pair\n```\n",
        block("https://ok2.example/f", type="atom"),
    )
    entries, errors = sources(fetch)
    assert [e["url"] for e in entries] == ["https://ok.example/f", "https://ok2.example/f"]
    assert [(e["code"], e["source"]) for e in errors] == [("MALFORMED_ENTRY", "anatomy/playbooks/intelligence/sources/core.md")] * 2
    assert {e["url"] for e in errors} == {"https://notype.example/f", "https://junk.example/f"}
    assert f.exists()
