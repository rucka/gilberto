import pytest

from fetch_helpers import block

ITEM = {"id": "1", "markdown": "---\ntype: article\n---\n\nbody\n"}


def entry(**over):
    return {"pillar": "intelligence", "contributor": "core", "url": "https://a.example/f", "type": "rss", **over}


def dispatch(fetch, utility, e, **env):
    return fetch.mod.dispatch(str(fetch.root), e, {"GILBERTO_UTILITY_PATH": utility.path, **env})


def code(fetch, utility, e, **env):
    with pytest.raises(fetch.mod.MechanicError) as ex:
        dispatch(fetch, utility, e, **env)
    return ex.value.code


def test_routes_by_type(fetch, utility):
    utility("utility-fetch-rss", [ITEM])
    assert dispatch(fetch, utility, entry()) == ("items", [ITEM])
    assert utility.args("utility-fetch-rss") == ["--url=https://a.example/f"]


def test_provider_wins_over_type(fetch, utility):
    utility("utility-fetch-rss", [ITEM])
    utility("utility-gmail-read", [{"id": "g", "markdown": "m"}])
    assert dispatch(fetch, utility, entry(provider="gmail", profile="p")) == ("items", [{"id": "g", "markdown": "m"}])


def test_profile_passed_through(fetch, utility):
    utility("utility-gmail-read", [ITEM])
    dispatch(fetch, utility, entry(provider="gmail", profile="learnn"))
    assert utility.args("utility-gmail-read") == ["--url=https://a.example/f", "--profile=learnn"]


def test_profile_omitted_goes_to_resolver(fetch, utility, monkeypatch):
    utility("utility-gmail-read", [ITEM])
    seen = []
    monkeypatch.setattr(fetch.mod, "resolve_profile", lambda root, e: seen.append(e["url"]) or "personal")
    dispatch(fetch, utility, entry(provider="gmail"))
    assert seen == ["https://a.example/f"]
    assert utility.args("utility-gmail-read") == ["--url=https://a.example/f", "--profile=personal"]


def test_explicit_profile_skips_resolver(fetch, utility, monkeypatch):
    utility("utility-gmail-read", [ITEM])
    monkeypatch.setattr(fetch.mod, "resolve_profile", lambda *a: pytest.fail("resolver called"))
    dispatch(fetch, utility, entry(provider="gmail", profile="learnn"))


def test_default_resolver_unresolved_is_typed_error(fetch, utility):
    utility("utility-gmail-read", [ITEM])
    assert code(fetch, utility, entry(provider="gmail")) == "PROFILE_UNRESOLVED"


def test_unavailable_fallback_mcp(fetch, utility):
    out = dispatch(fetch, utility, entry(provider="slack", profile="w", fallback="mcp"))
    assert out == ("mcp", {"provider": "slack", "profile": "w", "url": "https://a.example/f", "utility": "utility-slack-read"})


def test_unavailable_fallback_none_is_manual_hint(fetch, utility):
    kind, hint = dispatch(fetch, utility, entry(provider="slack", fallback="none"))
    assert kind == "manual" and "_ingest/" in hint["hint"]


def test_fallback_read_from_integration_file(fetch, utility):
    f = fetch.root / "anatomy/integrations/slack.md"
    f.parent.mkdir(parents=True)
    f.write_text("---\ntype: integration\nfallback: mcp\n---\n")
    assert dispatch(fetch, utility, entry(provider="slack"))[0] == "mcp"


def test_integration_without_fallback_defaults_to_manual(fetch, utility):
    f = fetch.root / "anatomy/integrations/slack.md"
    f.parent.mkdir(parents=True)
    f.write_text("---\ntype: integration\n---\n")
    assert dispatch(fetch, utility, entry(provider="slack"))[0] == "manual"


def test_available_utility_ignores_fallback(fetch, utility):
    utility("utility-slack-read", [ITEM])
    assert dispatch(fetch, utility, entry(provider="slack", profile="p", fallback="mcp"))[0] == "items"


def test_unknown_provider_and_type(fetch, utility):
    assert code(fetch, utility, entry(provider="nope")) == "UNKNOWN_PROVIDER"
    assert code(fetch, utility, entry(type="nope")) == "UNKNOWN_TYPE"


def test_invalid_fallback_value(fetch, utility):
    assert code(fetch, utility, entry(provider="slack", fallback="wat")) == "INVALID_FALLBACK"


@pytest.mark.parametrize(
    "kw",
    [
        {"code": 1, "stdout": '{"errors":[{"code":"auth"}]}'},
        {"code": 2, "stdout": "", "stderr": "boom"},
        {"stdout": "not json"},
        {"stdout": '{"items":[{"id":1}]}'},
        {"stdout": '{"items":"x"}'},
    ],
)
def test_utility_failure_is_typed(fetch, utility, kw):
    utility("utility-fetch-rss", **kw)
    assert code(fetch, utility, entry()) == "UTILITY_ERROR"


def test_utility_code_passed_through(fetch, utility):
    utility("utility-fetch-rss", code=1, stdout='{"errors":[{"code":"rate-limit"}]}')
    with pytest.raises(fetch.mod.MechanicError) as ex:
        dispatch(fetch, utility, entry())
    assert ex.value.extra["utility_code"] == "rate-limit" and ex.value.extra["utility"] == "utility-fetch-rss"
