import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"


def test_ac1_register_and_seed(mechanic, vault):
    code, out, _ = mechanic("forge-topic", "--slug=sleep", "--seed=pulse,intelligence", "--description=rest")
    assert code == 0 and out["status"] == "ok" and out["errors"] == []
    assert "| sleep | rest |" in (vault / "anatomy/topics.md").read_text()
    assert (vault / "pulse/sleep/history").is_dir()
    assert not (vault / "intelligence/sleep/history").exists()
    today = __import__("datetime").date.today().isoformat()
    for p in ("pulse", "intelligence"):
        text = (vault / p / "sleep/sleep.md").read_text()
        assert text == f'---\ntype: "{p}-topic"\ntopics: ["sleep"]\ncreated: "{today}"\nupdated: "{today}"\n---\n\n# Sleep\n'
    assert out["written"][-1] == "anatomy/topics.md"
    assert not list(vault.rglob("*.tmp.*"))


def test_ac1_default_no_seed_and_registry_byte_stable(mechanic, vault):
    before = (vault / "anatomy/topics.md").read_text()
    code, out, _ = mechanic("forge-topic", "--slug=sleep")
    assert code == 0 and out["written"] == ["anatomy/topics.md"]
    assert not (vault / "pulse/sleep").exists()
    after = (vault / "anatomy/topics.md").read_text()
    assert after == before.replace("| health | body |\n", "| health | body |\n| sleep |  |\n")


def test_seed_uses_template_when_present(mechanic, vault):
    tpl = vault / "anatomy/templates/intelligence/topic"
    tpl.mkdir(parents=True)
    (tpl / "topic.md").write_text("# {{TITLE}} {{SLUG}} {{DATE}}\n")
    mechanic("forge-topic", "--slug=deep-work", "--seed=intelligence")
    text = (vault / "intelligence/deep-work/deep-work.md").read_text()
    assert re.fullmatch(r"# Deep Work deep-work \d{4}-\d\d-\d\d\n", text)


def test_ac2_idempotent(mechanic, vault, tree):
    mechanic("forge-topic", "--slug=sleep", "--seed=pulse,intelligence")
    before = tree(vault)
    code, out, err = mechanic("forge-topic", "--slug=sleep", "--seed=pulse,intelligence")
    assert code == 0 and out["status"] == "skipped" and out["written"] == []
    assert "skipped (idempotent)" in err and tree(vault) == before


def test_rerun_heals_missing_seed_without_duplicate_entry(mechanic, vault):
    mechanic("forge-topic", "--slug=sleep")
    code, out, _ = mechanic("forge-topic", "--slug=sleep", "--seed=pulse")
    assert out["status"] == "ok" and "anatomy/topics.md" not in out["written"]
    assert (vault / "anatomy/topics.md").read_text().count("| sleep |") == 1
    assert (vault / "pulse/sleep/sleep.md").exists()


def test_existing_note_not_overwritten(mechanic, vault):
    (vault / "pulse/sleep").mkdir()
    (vault / "pulse/sleep/sleep.md").write_text("mine")
    mechanic("forge-topic", "--slug=sleep", "--seed=pulse")
    assert (vault / "pulse/sleep/sleep.md").read_text() == "mine"


@pytest.mark.parametrize("bad", ["../x", "..\\x", "/abs", "Upper", "a b", "é", "-x", "a" * 65, "sleep\n", ""])
def test_ac6_invalid_slug(mechanic, vault, tree, bad):
    before = tree(vault)
    code, out, _ = mechanic("forge-topic", f"--slug={bad}")
    assert code == 1 and out["errors"] == [{"code": "INVALID_SLUG", "input": bad}]
    assert tree(vault) == before


def test_ac7_invalid_seed_pillar(mechanic, vault, tree):
    before = tree(vault)
    code, out, _ = mechanic("forge-topic", "--slug=sleep", "--seed=pulse,ghost")
    assert code == 1 and out["errors"] == [{"code": "INVALID_SEED_PILLAR", "pillar": "ghost"}]
    assert tree(vault) == before


def test_missing_pillar_dir(mechanic, vault, tree):
    (vault / "pulse").rmdir()
    before = tree(vault)
    code, out, _ = mechanic("forge-topic", "--slug=sleep", "--seed=intelligence,pulse")
    assert code == 1 and out["errors"] == [{"code": "PILLAR_NOT_FOUND", "pillar": "pulse"}]
    assert tree(vault) == before


@pytest.mark.parametrize("name", ["me", "pulse", "projects", "intelligence", "journey", "network", "anatomy"])
def test_reserved_name(mechanic, vault, tree, name):
    before = tree(vault)
    code, out, _ = mechanic("forge-topic", f"--slug={name}")
    assert code == 1 and out["errors"] == [{"code": "RESERVED_NAME", "input": name}]
    assert tree(vault) == before


def test_registry_missing(mechanic, vault, tree):
    (vault / "anatomy/topics.md").unlink()
    before = tree(vault)
    code, out, _ = mechanic("forge-topic", "--slug=sleep", "--seed=pulse")
    assert code == 1 and out["errors"][0]["code"] == "REGISTRY_NOT_FOUND"
    assert tree(vault) == before


def test_missing_arg(mechanic):
    code, out, _ = mechanic("forge-topic")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_ARGS"


def test_symlinked_pillar_rejected(mechanic, vault, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (vault / "pulse").rmdir()
    os.symlink(outside, vault / "pulse")
    code, out, _ = mechanic("forge-topic", "--slug=sleep", "--seed=pulse")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_PATH"
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("fail_on", [1, 2, 3, 4])
def test_ac8_rollback_and_retry(mechanic, vault, tree, monkeypatch, fail_on):
    """replace #1/#2 = seed notes, #3 = registry (last). Any failure leaves nothing behind."""
    before = tree(vault)
    real, calls = os.replace, {"n": 0}

    def flaky(a, b):
        calls["n"] += 1
        if calls["n"] == fail_on:
            raise OSError(5, "EIO")
        return real(a, b)

    monkeypatch.setattr(os, "replace", flaky)
    code, out, _ = mechanic("forge-topic", "--slug=sleep", "--seed=pulse,intelligence")
    if fail_on == 4:  # only 3 writes exist: nothing fails
        assert code == 0
        return
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED"
    assert tree(vault) == before  # no registry entry, orphan note, folder or tmp file
    monkeypatch.setattr(os, "replace", real)
    code, out, _ = mechanic("forge-topic", "--slug=sleep", "--seed=pulse,intelligence")
    assert code == 0 and out["status"] == "ok"


def test_registry_last(mechanic, vault, monkeypatch):
    order = []
    real = os.replace
    monkeypatch.setattr(os, "replace", lambda a, b: (order.append(os.path.basename(b)), real(a, b))[1])
    mechanic("forge-topic", "--slug=sleep", "--seed=pulse")
    assert order == ["sleep.md", "topics.md"]


def test_sigint_between_tmp_write_and_mv(mechanic, vault, tree, monkeypatch):
    before = tree(vault)
    calls = {"n": 0}
    real = os.replace

    def interrupt(a, b):
        calls["n"] += 1
        if calls["n"] == 2:  # registry: notes already written
            raise KeyboardInterrupt
        return real(a, b)

    monkeypatch.setattr(os, "replace", interrupt)
    with pytest.raises(KeyboardInterrupt):
        mechanic("forge-topic", "--slug=sleep", "--seed=pulse")
    assert tree(vault) == before


def test_subprocess_smoke_twice(vault):
    env = {**os.environ, "GILBERTO_ROOT": str(vault)}
    cmd = [sys.executable, str(SCRIPT), "--slug=sleep", "--seed=pulse"]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert p.returncode == 0 and json.loads(p.stdout)["status"] == "ok"
    p2 = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert p2.returncode == 0 and json.loads(p2.stdout)["status"] == "skipped"
    assert "skipped (idempotent)" in p2.stderr
