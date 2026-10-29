import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"
BASE = ["--type=rss", "--url=https://example.com/feed.xml", "--cadence=daily", "--target-pillar=intelligence", "--target-topic=ai-news"]
CORE = "anatomy/playbooks/intelligence/sources/core.md"
BASELINE = "# Sources\n\n## Type mapping\n\n| Type | Utility |\n| ---- | ------- |\n| rss | utility-fetch-rss |\n\nTrailing prose.\n"


def args(**over):
    d = {a.split("=")[0]: a.split("=", 1)[1] for a in BASE}
    d = {k.lstrip("-"): v for k, v in d.items()}
    d.update({k.replace("_", "-"): v for k, v in over.items()})
    return [f"--{k}={v}" for k, v in d.items() if v is not None]


def seed(vault, text=BASELINE):
    f = vault / CORE
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    return f


def test_ac1_append_preserves_rest(mechanic, vault):
    f = seed(vault)
    code, out, _ = mechanic("forge-source", *args(contributor="core"))
    assert code == 0 and out == {"status": "ok", "written": [CORE], "skipped": [], "errors": []}
    text = f.read_text()
    assert text.startswith(BASELINE)
    assert text[len(BASELINE):] == '\n```yaml\n"https://example.com/feed.xml":\n  type: rss\n  cadence: daily\n  target_topic: ai-news\n```\n'
    assert not list(vault.rglob("*.tmp.*"))


def test_ac1_creates_file_and_dir_when_absent(mechanic, vault):
    code, out, _ = mechanic("forge-source", *args())
    assert code == 0 and out["written"] == [CORE]
    text = (vault / CORE).read_text()
    assert text.startswith("---\n") and '"https://example.com/feed.xml":' in text


def test_ac1_contributor_file_never_touches_core(mechanic, vault, tree):
    seed(vault)
    before = tree(vault)
    code, out, _ = mechanic("forge-source", *args(contributor="pulse-health", target_pillar="pulse"))
    assert code == 0 and out["written"] == ["anatomy/playbooks/pulse/sources/pulse-health.md"]
    after = tree(vault)
    assert after[CORE] == before[CORE]
    assert set(after) - set(before) >= {"anatomy/playbooks/pulse/sources/pulse-health.md"}


def test_ac2_idempotent_by_normalized_url(mechanic, vault, tree):
    mechanic("forge-source", *args(url="https://example.com"))
    before = tree(vault)
    for url in ("https://example.com", "https://example.com/", "HTTPS://EXAMPLE.com/"):
        code, out, err = mechanic("forge-source", *args(url=url, cadence="weekly"))
        assert code == 0 and out["status"] == "skipped" and out["written"] == [] and out["skipped"] == [CORE]
        assert "skipped (idempotent)" in err and tree(vault) == before


def test_ac2_dedup_reads_unquoted_key_and_other_urls_append(mechanic, vault):
    seed(vault, BASELINE + "```yaml\nhttps://a.com/x:\n  type: rss\n```\n")
    assert mechanic("forge-source", *args(url="https://a.com/x"))[1]["status"] == "skipped"
    assert mechanic("forge-source", *args(url="https://a.com/y"))[1]["status"] == "ok"
    assert mechanic("forge-source", *args(url="https://a.com/y"))[1]["status"] == "skipped"


@pytest.mark.parametrize("sep_text", ["", "x", "x\n", "x\n\n"])
def test_append_separator(mechanic, vault, sep_text):
    f = seed(vault, sep_text)
    mechanic("forge-source", *args())
    assert f.read_text().startswith(sep_text) and f.read_text().count("```yaml") == 1


@pytest.mark.parametrize(
    "over,code_",
    [
        ({"url": "../etc/passwd"}, "INVALID_URL"),
        ({"url": "https://example.com/../x"}, "INVALID_URL"),
        ({"url": "file:///etc/passwd"}, "INVALID_URL"),
        ({"url": "javascript:alert(1)"}, "INVALID_URL"),
        ({"contributor": "../core"}, "INVALID_SLUG"),
        ({"contributor": "/abs"}, "INVALID_SLUG"),
        ({"contributor": "Core"}, "INVALID_SLUG"),
        ({"contributor": "a" * 65}, "INVALID_SLUG"),
        ({"target_topic": "a b"}, "INVALID_SLUG"),
        ({"target_topic": "-lead"}, "INVALID_SLUG"),
        ({"type": "ftp"}, "INVALID_TYPE"),
        ({"cadence": "yearly"}, "INVALID_CADENCE"),
        ({"target_pillar": "ghost"}, "PILLAR_NOT_FOUND"),
        ({"target_pillar": "me"}, "PILLAR_DOES_NOT_HOLD_SOURCES"),
        ({"target_pillar": "projects"}, "PILLAR_DOES_NOT_HOLD_SOURCES"),
        ({"target_pillar": "network"}, "PILLAR_DOES_NOT_HOLD_SOURCES"),
    ],
)
def test_rejects_and_writes_nothing(mechanic, vault, tree, over, code_):
    before = tree(vault)
    code, out, _ = mechanic("forge-source", *args(**over))
    assert code == 1 and out["status"] == "error" and out["errors"][0]["code"] == code_
    assert tree(vault) == before


def test_missing_pillar_dir(mechanic, vault, tree):
    (vault / "journey").rmdir()
    before = tree(vault)
    code, out, _ = mechanic("forge-source", *args(target_pillar="journey"))
    assert code == 1 and out["errors"][0]["code"] == "PILLAR_NOT_FOUND" and tree(vault) == before


@pytest.mark.parametrize("t", ["rss", "atom", "youtube", "medical", "oura", "withings", "google-calendar", "outlook-calendar",
                               "icloud-calendar", "caldav", "gmail", "outlook-mail", "imap-mail", "apple-mail", "http"])
def test_all_types_accepted(mechanic, t):
    assert mechanic("forge-source", *args(type=t))[0] == 0


@pytest.mark.parametrize("c", ["realtime", "hourly", "daily", "weekly", "monthly"])
def test_all_cadences_accepted(mechanic, c):
    assert mechanic("forge-source", *args(cadence=c))[0] == 0


def test_missing_anatomy_dir(mechanic, vault, tree):
    import shutil

    shutil.rmtree(vault / "anatomy")
    code, out, _ = mechanic("forge-source", *args())
    assert code == 1 and out["errors"][0]["code"] == "REGISTRY_NOT_FOUND"


def test_write_failure_rolls_back_dirs(mechanic, vault, tree, monkeypatch):
    import os

    before = tree(vault)

    def boom(*_):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    code, out, _ = mechanic("forge-source", *args())
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED" and out["errors"][0]["rolledBack"]
    assert tree(vault) == before


def test_subprocess_smoke_double_run(vault):
    env = {"GILBERTO_ROOT": str(vault), "PATH": "/usr/bin:/bin"}
    outs = [json.loads(subprocess.run([sys.executable, str(SCRIPT), *args()], env=env, capture_output=True, text=True).stdout)
            for _ in range(2)]
    assert [o["status"] for o in outs] == ["ok", "skipped"]
