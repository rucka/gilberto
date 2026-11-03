from pathlib import Path

from fetch_helpers import block

ITEM = {"id": "1", "markdown": "m"}


def put(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def run(fetch, utility):
    return fetch(env={"GILBERTO_UTILITY_PATH": utility.path})


# AC7: source `profile:` honored, omitted -> real resolver (folder note > preferences > profile-unresolved)
def test_source_profile_honored_over_folder_note(fetch, source, utility):
    utility("utility-gmail-read", [ITEM])
    put(fetch.root, "intelligence/intelligence.md", "---\nconnectors: {gmail: other}\n---\n")
    source("intelligence", "core", block("https://m.example/i", provider="gmail", profile="learnn"))
    assert run(fetch, utility)[0] == 0
    assert utility.args("utility-gmail-read")[1] == "--profile=learnn"


def test_omitted_profile_resolved_from_folder_note_of_pillar(fetch, source, utility):
    utility("utility-gmail-read", [ITEM])
    put(fetch.root, "intelligence/intelligence.md", "---\nconnectors: {gmail: learnn}\n---\n")
    put(fetch.root, "anatomy/preferences.md", "## Integrations\n\ngmail: personal\n")
    source("intelligence", "core", block("https://m.example/i", provider="gmail"))
    assert run(fetch, utility)[0] == 0
    assert utility.args("utility-gmail-read") == ["--url=https://m.example/i", "--profile=learnn"]


def test_omitted_profile_falls_back_to_preferences(fetch, source, utility):
    utility("utility-gmail-read", [ITEM])
    put(fetch.root, "anatomy/preferences.md", "## Integrations\n\ngmail: personal\n")
    source("intelligence", "core", block("https://m.example/i", provider="gmail"))
    assert run(fetch, utility)[0] == 0
    assert utility.args("utility-gmail-read")[1] == "--profile=personal"


def test_omitted_profile_unresolved_is_per_source_error_no_utility_call(fetch, source, utility):
    utility("utility-gmail-read", [ITEM])
    utility("utility-fetch-rss", [ITEM])
    source("intelligence", "core", block("https://m.example/i", provider="gmail"), block("https://m.example/r", type="rss"))
    code, out, _ = run(fetch, utility)
    assert code == 1 and [e["code"] for e in out["errors"]] == ["PROFILE_UNRESOLVED"] and len(out["written"]) == 1
    assert not (Path(utility.path) / "utility-gmail-read" / "args.json").exists()


def test_type_routed_entry_never_resolves_profile(fetch, source, utility):
    utility("utility-fetch-rss", [ITEM])
    source("intelligence", "core", block("https://m.example/r", type="rss"))
    assert run(fetch, utility)[0] == 0 and utility.args("utility-fetch-rss") == ["--url=https://m.example/r"]


# AC4 via shared runner: script wins; mcp / manual skipped
def test_fallbacks_still_skipped_with_resolved_profile(fetch, source, utility):
    put(fetch.root, "anatomy/preferences.md", "## Integrations\n\nslack: work\n")
    source("intelligence", "core", block("https://m.example/s", provider="slack", fallback="mcp"), block("https://m.example/t", provider="slack", fallback="none"))
    code, out, _ = run(fetch, utility)
    assert code == 0 and [s["reason"] for s in out["skipped"]] == ["mcp-fallback", "manual"]
    assert "_ingest/" in out["skipped"][1]["hint"]


def test_omitted_profile_resolved_for_integration_lookup_and_mcp_request(fetch, source, utility):
    put(fetch.root, "anatomy/integrations/slack/work.md", "---\ntype: integration\nfallback: mcp\n---\n")
    put(fetch.root, "anatomy/preferences.md", "## Integrations\n\nslack: work\n")
    source("intelligence", "core", block("https://m.example/s", provider="slack"))
    code, out, _ = run(fetch, utility)
    assert code == 0 and out.get("errors", []) == []
    assert [(s["reason"], s["profile"]) for s in out["skipped"]] == [("mcp-fallback", "work")]


def test_omitted_profile_no_utility_folder_note_beats_preferences_and_flat_layout(fetch, source, utility):
    put(fetch.root, "intelligence/intelligence.md", "---\nconnectors: {slack: work}\n---\n")
    put(fetch.root, "anatomy/preferences.md", "## Integrations\n\nslack: personal\n")
    put(fetch.root, "anatomy/integrations/slack/work.md", "---\ntype: integration\nfallback: mcp\n---\n")
    put(fetch.root, "anatomy/integrations/slack/personal.md", "---\ntype: integration\nfallback: none\n---\n")
    put(fetch.root, "anatomy/integrations/slack.md", "---\ntype: integration\nfallback: none\n---\n")
    source("intelligence", "core", block("https://m.example/s", provider="slack"))
    code, out, _ = run(fetch, utility)
    assert code == 0 and out.get("errors", []) == []
    assert [(s["reason"], s["profile"]) for s in out["skipped"]] == [("mcp-fallback", "work")]


def test_omitted_profile_unresolvable_no_utility_falls_through_to_default_layout(fetch, source, utility):
    put(fetch.root, "anatomy/integrations/slack/default.md", "---\ntype: integration\nfallback: mcp\n---\n")
    source("intelligence", "core", block("https://m.example/s", provider="slack"))
    code, out, _ = run(fetch, utility)
    assert code == 0 and out.get("errors", []) == []
    assert [s["reason"] for s in out["skipped"]] == ["mcp-fallback"]


# #71 wiring: provenance on ingested notes (AC1)
def test_provider_items_carry_source_profile(fetch, source, utility):
    utility("utility-gmail-read", [{"id": "1", "markdown": "---\ntitle: t\n---\nbody\n"}])
    put(fetch.root, "anatomy/preferences.md", "## Integrations\n\ngmail: personal\n")
    source("intelligence", "core", block("https://m.example/i", provider="gmail"))
    code, out, _ = run(fetch, utility)
    assert code == 0
    fm, body = fetch.mod.frontmatter.parse((fetch.root / out["written"][0]).read_text())
    assert fm["source_profile"] == "gmail:personal" and fm["title"] == "t" and body == "body\n"


def test_type_items_have_no_source_profile(fetch, source, utility):
    utility("utility-fetch-rss", [ITEM])
    source("intelligence", "core", block("https://m.example/f", type="rss"))
    code, out, _ = run(fetch, utility)
    assert code == 0 and "source_profile" not in (fetch.root / out["written"][0]).read_text()


# #71 wiring: integration-file reading owned by _lib.integrations
def test_dispatcher_reads_integration_via_lib(fetch, source, utility, monkeypatch):
    seen = []
    real = fetch.mod.integrations.integration_path
    monkeypatch.setattr(fetch.mod.integrations, "integration_path", lambda *a: seen.append(a[1:]) or real(*a))
    put(fetch.root, "anatomy/integrations/slack.md", "---\ntype: integration\nfallback: mcp\n---\n")
    source("intelligence", "core", block("https://m.example/s", provider="slack", profile="default"))
    code, out, _ = run(fetch, utility)
    assert code == 0 and seen == [("slack", "default")]
    assert [s["reason"] for s in out["skipped"]] == ["mcp-fallback"]
