import json

import pytest

from _lib import connector, frontmatter
from _lib.connector import ConnectorError


def test_normalize_adds_canonical_frontmatter():  # AC1
    out = connector.normalize_item("# Hi\n", "https://a.example/x", "google:learnn", created="2026-11-02")
    fm, body = frontmatter.parse(out)
    assert fm == {"type": "intelligence-source", "source": "https://a.example/x", "created": "2026-11-02", "source_profile": "google:learnn"}
    assert body == "# Hi\n"


def test_normalize_keeps_extra_keys_and_overrides_canonical():  # AC1
    md = '---\ntitle: "T"\nsource: "x"\nsource_profile: "evil:p"\n---\nbody\n'
    fm, body = frontmatter.parse(connector.normalize_item(md, "https://a.example/x", "google:default", type="gmail-message"))
    assert fm["title"] == "T" and fm["source"] == "https://a.example/x"
    assert fm["source_profile"] == "google:default" and fm["type"] == "gmail-message" and fm["created"]
    assert body == "body\n"


@pytest.mark.parametrize("profile", ["google", "google:", ":p", "a:b:c", "", None])
def test_normalize_rejects_bad_profile(profile):  # AC1
    with pytest.raises(ConnectorError) as e:
        connector.normalize_item("x", "u", profile)
    assert e.value.code == "provider"


@pytest.mark.parametrize("code", ["auth", "rate-limit", "not-found", "provider", "profile-unresolved"])
def test_error_codes_accepted(code):  # AC2
    assert ConnectorError(code).as_dict() == {"code": code}


def test_error_code_outside_set_rejected():  # AC2
    with pytest.raises(ValueError):
        ConnectorError("boom")


def test_run_utility_error_exit_nonzero_and_payload(capsys):  # AC2
    def fn(argv, env):
        raise ConnectorError("auth")

    assert connector.run_utility(fn, [], {}) == 1
    assert json.loads(capsys.readouterr().out) == {"errors": [{"code": "auth"}]}


def test_run_utility_ok_emits_items(capsys):  # AC1
    assert connector.run_utility(lambda a, e: [{"id": "1", "markdown": "m"}], [], {}) == 0
    assert json.loads(capsys.readouterr().out) == {"items": [{"id": "1", "markdown": "m"}]}


def test_run_utility_unexpected_oserror_is_provider_error(capsys):  # AC2
    def fn(argv, env):
        raise OSError("down")

    assert connector.run_utility(fn, [], {}) == 1
    assert json.loads(capsys.readouterr().out)["errors"][0]["code"] == "provider"


def _flaky(errors):
    calls = []

    def fn():
        calls.append(1)
        if len(calls) <= len(errors):
            raise errors[len(calls) - 1]
        return "ok"

    return fn, calls


def test_retry_rate_limit_then_success_backs_off():  # AC2
    fn, calls = _flaky([ConnectorError("rate-limit"), ConnectorError("rate-limit")])
    sleeps = []
    assert connector.retry(fn, sleep=sleeps.append) == "ok"
    assert len(calls) == 3 and sleeps == [0.5, 1.0]


def test_retry_transient_oserror():  # AC2
    fn, calls = _flaky([TimeoutError("t")])
    assert connector.retry(fn, sleep=lambda s: None) == "ok" and len(calls) == 2


def test_retry_exhausted_raises_last():  # AC2
    fn, calls = _flaky([ConnectorError("rate-limit")] * 5)
    with pytest.raises(ConnectorError) as e:
        connector.retry(fn, attempts=3, sleep=lambda s: None)
    assert e.value.code == "rate-limit" and len(calls) == 3


@pytest.mark.parametrize("code", ["auth", "not-found", "provider", "profile-unresolved"])
def test_retry_does_not_retry_permanent(code):  # AC2
    fn, calls = _flaky([ConnectorError(code)])
    with pytest.raises(ConnectorError):
        connector.retry(fn, sleep=lambda s: pytest.fail("slept"))
    assert len(calls) == 1


def test_state_dedup_second_read_emits_nothing(tmp_path):  # AC3
    path = tmp_path / "s" / "_state.json"
    items = [{"id": "a", "markdown": "1"}, {"id": "b", "markdown": "2"}]
    st = connector.load_state(path)
    assert [i["id"] for i in connector.new_items(st, "u", items)] == ["a", "b"]
    connector.save_state(path, st)
    assert json.loads(path.read_text()) == {"u": {"fetched": ["a", "b"]}}
    st = connector.load_state(path)
    assert connector.new_items(st, "u", items + [{"id": "c", "markdown": "3"}]) == [{"id": "c", "markdown": "3"}]


def test_state_dedup_within_one_batch():  # AC3
    assert len(connector.new_items({}, "u", [{"id": "a"}, {"id": "a"}])) == 1


@pytest.mark.parametrize("content", ["", "{not json", "[]", '{"u": 3}', '{"u": {"fetched": "x"}}', b"\xff\xfe"])
def test_state_corrupt_is_empty_and_rewritten_atomically(tmp_path, content):  # AC3 edge
    path = tmp_path / "_state.json"
    path.write_bytes(content if isinstance(content, bytes) else content.encode())
    st = connector.load_state(path)
    assert st == {}
    connector.new_items(st, "u", [{"id": "a"}])
    connector.save_state(path, st)
    assert json.loads(path.read_text()) == {"u": {"fetched": ["a"]}}
    assert [p.name for p in tmp_path.iterdir()] == ["_state.json"]


def test_state_missing_is_empty(tmp_path):  # AC3 edge
    assert connector.load_state(tmp_path / "nope" / "_state.json") == {}
