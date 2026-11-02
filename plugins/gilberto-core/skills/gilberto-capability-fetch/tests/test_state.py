import json

from fetch_helpers import block

URL = "https://a.example/f"
A = {"id": "a", "markdown": "---\ntype: article\n---\n\nA\n"}
B = {"id": "b", "markdown": "---\ntype: article\n---\n\nB\n"}
STATE = "anatomy/playbooks/intelligence/sources/core/_state.json"


def run(fetch, utility, *argv):
    return fetch(*argv, env={"GILBERTO_UTILITY_PATH": utility.path})


def seed(source, *blocks):
    return source("intelligence", "core", *(blocks or (block(URL, type="rss"),)))


def test_writes_items_to_ingest_and_reports(fetch, source, utility):
    seed(source)
    utility("utility-fetch-rss", [A, B])
    code, out, _ = run(fetch, utility)
    assert code == 0 and out["status"] == "ok" and out["skipped"] == [] and out["errors"] == []
    assert len(out["written"]) == 2 and all(p.startswith("_ingest/") for p in out["written"])
    assert (fetch.root / out["written"][0]).read_text() == A["markdown"]


def test_rerun_skips_fetched_items_and_is_idempotent(fetch, source, utility, tree):
    seed(source)
    utility("utility-fetch-rss", [A])
    _, first, _ = run(fetch, utility)
    before = tree(fetch.root)
    code, out, _ = run(fetch, utility)
    assert code == 0 and out["status"] == "skipped" and out["written"] == []
    assert out["skipped"] == [{"path": first["written"][0], "reason": "already-fetched"}]
    assert tree(fetch.root) == before


def test_rerun_fetches_only_new_items(fetch, source, utility):
    seed(source)
    utility("utility-fetch-rss", [A])
    run(fetch, utility)
    utility("utility-fetch-rss", [A, B])
    _, out, _ = run(fetch, utility)
    assert len(out["written"]) == 1 and len(out["skipped"]) == 1
    assert sorted(json.loads((fetch.root / STATE).read_text())[URL]["fetched"]) == ["a", "b"]


def test_state_is_per_source_url(fetch, source, utility):
    seed(source, block(URL, type="rss"), block("https://b.example/f", type="rss"))
    utility("utility-fetch-rss", [A])
    _, out, _ = run(fetch, utility)
    assert len(out["written"]) == 2 and len(set(out["written"])) == 2


def test_duplicate_id_in_one_run_written_once(fetch, source, utility):
    seed(source)
    utility("utility-fetch-rss", [A, A])
    _, out, _ = run(fetch, utility)
    assert len(out["written"]) == 1 and len(out["skipped"]) == 1


def test_writes_confined_to_ingest_and_state(fetch, source, utility, tree):
    seed(source)
    utility("utility-fetch-rss", [A])
    before = tree(fetch.root)
    run(fetch, utility)
    changed = {k for k, v in tree(fetch.root).items() if before.get(k, "new") != v}
    assert changed and all(k.startswith("_ingest") or k.endswith("_state.json") or k.endswith("core") for k in changed), changed
    assert not [k for k in tree(fetch.root) if ".tmp." in k]


def test_failure_isolated_exit_status_and_state_untouched(fetch, source, utility):
    seed(source, block("https://bad.example/f", type="nope"), block(URL, type="rss"), block("https://m.example/f", type="rss", provider="slack", fallback="mcp"))
    utility("utility-fetch-rss", [A])
    code, out, err = run(fetch, utility)
    assert code == 1 and out["status"] == "partial"
    assert [(e["code"], e["url"]) for e in out["errors"]] == [("UNKNOWN_TYPE", "https://bad.example/f")]
    assert len(out["written"]) == 1
    assert out["skipped"] == [{"source": "anatomy/playbooks/intelligence/sources/core.md", "url": "https://m.example/f", "reason": "mcp-fallback", "provider": "slack", "profile": None, "utility": "utility-slack-read"}]


def test_utility_error_keeps_other_sources_and_state(fetch, source, utility):
    seed(source, block(URL, type="rss"), block("https://h.example/f", type="http"))
    utility("utility-fetch-rss", code=1, stdout='{"errors":[{"code":"auth"}]}')
    utility("utility-download-html", [B])
    code, out, _ = run(fetch, utility)
    assert code == 1 and out["errors"][0]["code"] == "UTILITY_ERROR" and len(out["written"]) == 1
    state = json.loads((fetch.root / STATE).read_text())
    assert URL not in state and "https://h.example/f" in state


def test_all_failed_status_error(fetch, source, utility):
    seed(source, block("https://bad.example/f", type="nope"))
    code, out, _ = run(fetch, utility)
    assert code == 1 and out["status"] == "error"


def test_manual_hint_skipped_not_failure(fetch, source, utility):
    seed(source, block(URL, type="rss", provider="slack", fallback="none"))
    code, out, _ = run(fetch, utility)
    assert code == 0 and out["status"] == "skipped" and out["skipped"][0]["reason"] == "manual" and "_ingest/" in out["skipped"][0]["hint"]


def test_corrupt_state_is_error_and_untouched(fetch, source, utility):
    seed(source)
    f = fetch.root / STATE
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("{nope")
    utility("utility-fetch-rss", [A])
    code, out, _ = run(fetch, utility)
    assert code == 1 and out["errors"][0]["code"] == "STATE_CORRUPT" and out["written"] == []
    assert f.read_text() == "{nope"


def test_loader_errors_reported_in_result(fetch, source, utility):
    seed(source, block("https://x.example/f", cadence="daily"), block(URL, type="rss"))
    utility("utility-fetch-rss", [A])
    code, out, _ = run(fetch, utility)
    assert code == 1 and out["errors"][0]["code"] == "MALFORMED_ENTRY" and len(out["written"]) == 1


def test_filters_via_cli(fetch, source, utility):
    seed(source)
    source("pulse", "core", block("https://p.example/f", type="rss"))
    utility("utility-fetch-rss", [A])
    _, out, _ = run(fetch, utility, "--pillar=pulse")
    assert len(out["written"]) == 1 and not (fetch.root / STATE).exists()
    _, out, _ = run(fetch, utility, "--source=https://a.example/f")
    assert len(out["written"]) == 1


def test_empty_vault_noop_success(fetch, utility):
    code, out, _ = run(fetch, utility)
    assert code == 0 and out == {"status": "ok", "written": [], "skipped": [], "errors": []}


def test_invalid_root_and_args(fetch):
    code, out, _ = fetch("--bogus", env={})
    assert code == 1 and out["status"] == "error" and out["errors"][0]["code"] == "INVALID_ARGS"
    code, out, _ = fetch(env={"GILBERTO_ROOT": "/nonexistent-x"})
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH"
