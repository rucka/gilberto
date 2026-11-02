import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_helpers import block  # noqa: E402

ITEM = {"id": "1", "markdown": "x\n"}


@pytest.mark.parametrize("key", ["gmail-read/../../outside/evil", "../evil", "Evil", "a/b"])
def test_us71_r2_provider_not_slug_is_typed_error_never_executed(fetch, source, utility, tmp_path, key):
    evil = tmp_path / "outside" / "evil-read"
    evil.mkdir(parents=True)
    (evil / "script.py").write_text("open(__file__ + '.ran', 'w').write('1')\n")
    utility("utility-rss-read", [ITEM])
    source("intelligence", "core", block("https://a.example/bad", provider=key), block("https://a.example/ok", provider="rss", profile="p"))
    code, out, _ = fetch(env={"GILBERTO_UTILITY_PATH": utility.path})
    assert code == 1
    assert [e["code"] for e in out["errors"]] == ["INVALID_PROVIDER"]
    assert len(out["written"]) == 1
    assert not (evil / "script.py.ran").exists()


def test_us71_r2_invalid_type_is_typed_error(fetch, source, utility):
    source("intelligence", "core", block("https://a.example/bad", type="../x"))
    code, out, _ = fetch(env={"GILBERTO_UTILITY_PATH": utility.path})
    assert code == 1 and [e["code"] for e in out["errors"]] == ["INVALID_TYPE"]


@pytest.mark.parametrize("value", [["a"], "a", 1, None])
def test_us71_r2_non_object_state_value_is_state_corrupt(fetch, source, utility, value):
    utility("utility-fetch-rss", [ITEM])
    source("intelligence", "core", block("https://a.example/f", type="rss"))
    source("intelligence", "other", block("https://b.example/f", type="rss"))
    st = fetch.root / "anatomy/playbooks/intelligence/sources/core/_state.json"
    st.parent.mkdir(parents=True)
    st.write_text(json.dumps({"https://a.example/f": value}))
    code, out, _ = fetch(env={"GILBERTO_UTILITY_PATH": utility.path})
    assert code == 1
    assert [e["code"] for e in out["errors"]] == ["STATE_CORRUPT"]
    assert len(out["written"]) == 1
    assert json.loads(st.read_text()) == {"https://a.example/f": value}


def test_us71_r2_resolver_typed_error_isolated(fetch, source, utility, monkeypatch):
    """#60 seam: resolver raising profile-unresolved is a per-source typed error."""
    utility("utility-slack-read", [ITEM])
    utility("utility-fetch-rss", [ITEM])

    def unresolved(root, entry):
        raise fetch.mod.MechanicError("PROFILE_UNRESOLVED", provider=entry["provider"])

    monkeypatch.setattr(fetch.mod, "resolve_profile", unresolved)
    source("intelligence", "core", block("https://a.example/s", provider="slack"), block("https://a.example/r", type="rss"))
    code, out, _ = fetch(env={"GILBERTO_UTILITY_PATH": utility.path})
    assert code == 1 and [e["code"] for e in out["errors"]] == ["PROFILE_UNRESOLVED"]
    assert len(out["written"]) == 1


def test_us71_r2_skill_md_backticks_balanced():
    md = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text()
    for line in md.splitlines():
        if not line.startswith("```"):
            assert line.count("`") % 2 == 0, line
