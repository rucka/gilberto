import os

import pytest

from _lib import integrations, vault_io
from _lib.connector import ConnectorError
from _lib.result import MechanicError


@pytest.fixture
def root(tmp_path):
    (tmp_path / "v").mkdir()
    return vault_io.vault_root({"GILBERTO_ROOT": str(tmp_path / "v")})


def put(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)
    return p


def cfg(root, rel="anatomy/integrations/google/learnn.md", body='type: integration\nprovider: google\nfallback: mcp\n'):
    return put(root, rel, f"---\n{body}---\n\n# cfg\n")


# AC5 -------------------------------------------------------------------
def test_valid_config_returned(root):
    fm = integrations.validate_integration(cfg(root, body='type: integration\nprovider: google\nprofile: learnn\naccounts: [a@b.example]\nscopes: [mail.read]\nfallback: mcp\nauto_write: ["calendar:create-event"]\nsecret: keychain:gilberto/google/learnn\n'))
    assert fm["fallback"] == "mcp" and fm["accounts"] == ["a@b.example"] and fm["secret"] == "keychain:gilberto/google/learnn"


def reason(root, body, text=None):
    p = put(root, "anatomy/integrations/x/default.md", text) if text is not None else cfg(root, body=body)
    with pytest.raises(MechanicError) as e:
        integrations.validate_integration(p)
    assert e.value.code == "INVALID_INTEGRATION"
    return e.value.extra


def test_unknown_key_rejected(root):
    assert reason(root, "type: integration\nwhatever: 1\n")["keys"] == ["whatever"]


@pytest.mark.parametrize("key", ["token", "password", "api_key", "client_secret"])
def test_secret_named_key_rejected(root, key):
    assert reason(root, f"type: integration\n{key}: abc\n")["keys"] == [key]


@pytest.mark.parametrize("value", [
    "xoxb-123456789012-abcdefghijkl",
    "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
    "sk-abcdefghijklmnopqrstuvwxyz012345",
    "AKIAABCDEFGHIJKLMNOP",
    "Bearer abcdefghijklmnop",
    "abcdEFGH0123456789abcdEFGH0123456789",
])
@pytest.mark.parametrize("where", ["accounts", "channels", "secret"])
def test_secret_looking_value_rejected(root, value, where):
    body = f'type: integration\n{where}: ["{value}"]\n' if where != "secret" else f"type: integration\nsecret: {value}\n"
    assert reason(root, body)["reason"]


def test_secret_must_be_reference(root):
    assert reason(root, "type: integration\nsecret: hunter2\n")["reason"]


def test_send_never_allowlistable(root):
    assert "send" in reason(root, 'type: integration\nauto_write: ["slack:send", "calendar:create-event"]\n')["reason"]


@pytest.mark.parametrize("fallback", ["maybe", "MCP", 1])
def test_bad_fallback_rejected(root, fallback):
    assert reason(root, f"type: integration\nfallback: {fallback}\n")["reason"]


@pytest.mark.parametrize("text", ["# no frontmatter\n", "---\ntype: integration\nnever closed\n", "---\ntype: integration\ngarbage line\n---\n"])
def test_malformed_is_typed_error_not_crash(root, text):
    assert reason(root, None, text)["reason"]


def test_missing_file_typed(root):
    with pytest.raises(MechanicError) as e:
        integrations.validate_integration(os.path.join(root, "nope.md"))
    assert e.value.code == "INVALID_INTEGRATION"


def test_path_default_profile_and_flat_compat(root):
    assert integrations.integration_path(root, "google", "learnn") is None
    flat = put(root, "anatomy/integrations/google.md", "---\ntype: integration\n---\n")
    assert integrations.integration_path(root, "google") == flat
    assert integrations.integration_path(root, "google", "default") == flat
    assert integrations.integration_path(root, "google", "learnn") is None  # compat is for `default` only
    d = cfg(root, "anatomy/integrations/google/default.md")
    assert integrations.integration_path(root, "google") == d  # profile file wins over flat


@pytest.mark.parametrize("profile", ["../x", "a/b", "A", ""])
def test_path_rejects_non_slug_profile(root, profile):
    with pytest.raises(MechanicError) as e:
        integrations.integration_path(root, "google", profile)
    assert e.value.code == "INVALID_PROFILE"


# AC6 / AC7 -------------------------------------------------------------
def note(root, folder, fm_body):
    name = os.path.basename(folder)
    return put(root, f"{folder}/{name}.md", f"---\ntype: project-index\n{fm_body}---\n")


def prefs(root, line="google: personal"):
    put(root, "anatomy/preferences.md", f"---\ntype: preferences\n---\n\n## Cadences\n\nx\n\n## Integrations\n\n{line}\n\n## Other\n\ngoogle: nope\n")


def res(root, target, provider="google", explicit=None):
    return integrations.resolve_profile(root, target, provider, explicit)


def test_explicit_wins_over_everything(root):
    note(root, "projects/acme", "connectors: {google: learnn}\n")
    prefs(root)
    assert res(root, "projects/acme/x.md", explicit="work") == "work"


def test_explicit_non_slug_rejected(root):
    with pytest.raises(MechanicError) as e:
        res(root, "projects", explicit="../x")
    assert e.value.code == "INVALID_PROFILE"


def test_nearest_folder_note_wins_nested(root):
    note(root, "projects/acme", "connectors: {google: learnn, slack: acme}\n")
    note(root, "projects/acme/sub", "connectors: {google: inner}\n")
    note(root, "projects", "connectors: {google: outer}\n")
    prefs(root)
    assert res(root, "projects/acme/sub/deep/file.md") == "inner"
    assert res(root, "projects/acme/other/file.md") == "learnn"
    assert res(root, "projects/acme/sub/deep/file.md", provider="slack") == "acme"
    assert res(root, "projects/other.md") == "outer"


def test_folder_note_without_connectors_keeps_walking(root):
    note(root, "projects/acme", "connectors: {google: learnn}\n")
    note(root, "projects/acme/sub", "status: active\n")
    note(root, "projects/acme/sub/leaf", "connectors: {slack: x}\n")
    assert res(root, "projects/acme/sub/leaf/f.md") == "learnn"


def test_block_style_connectors(root):
    note(root, "projects/acme", "connectors:\n  google: learnn\n  slack: w\n")
    assert res(root, "projects/acme/f.md") == "learnn"


def test_json_style_connectors(root):
    note(root, "projects/acme", 'connectors: {"google": "learnn"}\n')
    assert res(root, "projects/acme/f.md") == "learnn"


def test_falls_back_to_preferences_section_only(root):
    prefs(root)
    assert res(root, "projects/acme/f.md") == "personal"


def test_preferences_bullet_form_and_other_section_ignored(root):
    prefs(root, "- slack: work")
    with pytest.raises(ConnectorError) as e:
        res(root, "projects/f.md")  # `google: nope` sits under another section
    assert e.value.code == "profile-unresolved"


def test_missing_profile_is_error_never_guess(root):
    with pytest.raises(ConnectorError) as e:
        res(root, "projects/acme/f.md")
    assert e.value.code == "profile-unresolved" and e.value.extra["provider"] == "google"


def test_single_profile_is_not_guessed(root):
    cfg(root)
    with pytest.raises(ConnectorError):
        res(root, "projects/f.md")


def test_walk_stops_at_vault_root(root, tmp_path):
    put(str(tmp_path), "v.md", "---\nconnectors: {google: above}\n---\n")  # sibling of vault root
    put(str(tmp_path), "connectors.md", "---\nconnectors: {google: above}\n---\n")
    with pytest.raises(ConnectorError):
        res(root, "projects/f.md")


def test_target_escaping_root_rejected(root):
    with pytest.raises(MechanicError) as e:
        res(root, "../outside/f.md")
    assert e.value.code == "INVALID_PATH"


def test_symlink_escape_not_followed(root, tmp_path):
    out = tmp_path / "outside"
    out.mkdir()
    (out / "outside.md").write_text("---\nconnectors: {google: leaked}\n---\n")
    os.symlink(out, os.path.join(root, "link"))
    with pytest.raises(MechanicError) as e:
        res(root, "link/f.md")
    assert e.value.code == "INVALID_PATH"


def test_malformed_folder_note_typed_error(root):
    put(root, "projects/acme/acme.md", "---\nconnectors: {google: x}\nnever closed\n")
    with pytest.raises(MechanicError) as e:
        res(root, "projects/acme/f.md")
    assert e.value.code == "INVALID_FOLDER_NOTE"


def test_connector_value_not_slug_rejected(root):
    note(root, "projects/acme", "connectors: {google: ../x}\n")
    with pytest.raises(MechanicError) as e:
        res(root, "projects/acme/f.md")
    assert e.value.code == "INVALID_PROFILE"


def test_nonexistent_target_dir_still_walks_up(root):
    note(root, "projects", "connectors: {google: p}\n")
    assert res(root, "projects/not/yet/created/") == "p"


# AC4 -------------------------------------------------------------------
def test_runner_script_wins_over_fallback():
    assert integrations.resolve_runner("/x/script.py", "mcp") == {"kind": "script", "path": "/x/script.py"}


def test_runner_mcp_fallback():
    assert integrations.resolve_runner(None, "mcp") == {"kind": "skipped", "reason": "mcp-fallback"}


@pytest.mark.parametrize("fallback", ["none", None])
def test_runner_manual_has_ingest_hint(fallback):
    out = integrations.resolve_runner(None, fallback)
    assert out["kind"] == "skipped" and out["reason"] == "manual" and "_ingest/" in out["hint"]


def test_runner_invalid_fallback_typed():
    with pytest.raises(MechanicError) as e:
        integrations.resolve_runner(None, "maybe")
    assert e.value.code == "INVALID_FALLBACK"


# AC8 -------------------------------------------------------------------
def guard(root, op="write", action="calendar:create-event", unattended=True, auto_write=(), summary="s"):
    return integrations.guard_write(root, "google", "learnn", op, action, unattended, auto_write, summary)


def tasks(root):
    p = os.path.join(root, "journey/tasks.md")
    return open(p).read() if os.path.exists(p) else None


@pytest.mark.parametrize("op", ["read", "search"])
def test_reads_never_guarded(root, op):
    assert guard(root, op=op)["decision"] == "allow" and tasks(root) is None


def test_attended_write_asks_confirmation_no_task(root):
    assert guard(root, unattended=False)["decision"] == "confirm" and tasks(root) is None


def test_attended_allowlisted_write_allowed(root):
    assert guard(root, unattended=False, auto_write=["calendar:create-event"])["decision"] == "allow"


def test_unattended_allowlisted_write_allowed(root):
    assert guard(root, auto_write=["calendar:create-event"])["decision"] == "allow" and tasks(root) is None


@pytest.mark.parametrize("op", ["write", "delete"])
def test_unattended_not_allowlisted_becomes_pending_task(root, op):
    out = guard(root, op=op, auto_write=["other:thing"], summary="Create meeting X")
    assert out["decision"] == "pending" and out["path"] == "journey/tasks.md"
    t = tasks(root)
    assert t.count("- [ ]") == 1 and "google:learnn" in t and "calendar:create-event" in t and "Create meeting X" in t and "pending confirmation" in t


def test_pending_tasks_append_not_overwrite(root):
    put(root, "journey/tasks.md", "---\ntype: tasks\n---\n\n- [ ] existing\n")
    guard(root, summary="one")
    guard(root, action="calendar:delete-event", op="delete", summary="two")
    t = tasks(root)
    assert "existing" in t and "one" in t and "two" in t and t.count("- [ ]") == 3


def test_pending_task_is_idempotent(root):
    guard(root, summary="one")
    guard(root, summary="one")
    assert tasks(root).count("- [ ]") == 1


@pytest.mark.parametrize("unattended", [True, False])
def test_send_never_allowlistable(root, unattended):
    out = guard(root, op="send", action="slack:send", unattended=unattended, auto_write=["slack:send"])
    assert out["decision"] == ("pending" if unattended else "confirm")


def test_unknown_op_typed(root):
    with pytest.raises(MechanicError) as e:
        guard(root, op="explode")
    assert e.value.code == "INVALID_OP"


@pytest.mark.parametrize("env,expected", [({"GILBERTO_UNATTENDED": "1"}, True), ({}, False), ({"GILBERTO_UNATTENDED": "0"}, False)])
def test_is_unattended(env, expected):
    assert integrations.is_unattended(env) is expected


def test_long_email_and_scope_url_are_not_secrets(root):
    fm = integrations.validate_integration(cfg(root, body='type: integration\naccounts: [averyveryveryverylongaddress.name@example.com]\nscopes: ["https://www.googleapis.com/auth/gmail.readonly"]\n'))
    assert len(fm["accounts"][0]) > 32
