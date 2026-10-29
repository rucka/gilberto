import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from _lib import frontmatter

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"
FM = {
    "triggers": [{"cron": "0 7 * * *"}, {"keyword": "buongiorno gilberto"}],
    "dispatch_to": ["gilberto-capability-pulse-summarize", "gilberto-capability-journey-recall"],
    "silence_learned": [],
}


def play(mechanic, event="morning-briefing", domain="surface", mode="core", fm=FM, contributor=None, **kw):
    argv = [f"--event={event}", f"--domain={domain}", f"--mode={mode}", f"--frontmatter={json.dumps(fm)}"]
    if contributor:
        argv.append(f"--contributor={contributor}")
    return mechanic("forge-playbook", *argv, **kw)


def test_ac4_core_mode(mechanic, vault):
    code, out, _ = play(mechanic)
    rel = "anatomy/playbooks/surface/morning-briefing.md"
    assert code == 0 and out == {"status": "ok", "written": [rel], "skipped": [], "errors": []}
    fm, body = frontmatter.parse((vault / rel).read_text())
    assert fm == {"event": "morning-briefing", **FM} and list(fm) == ["event", "triggers", "dispatch_to", "silence_learned"]
    assert body.strip().startswith("# Morning Briefing") and "Placeholder" in body
    assert not list(vault.rglob("*.tmp.*"))


@pytest.mark.parametrize("domain", ["ingest", "structure", "surface", "act", "reflect", "next"])
def test_all_domains(mechanic, vault, domain):
    assert play(mechanic, domain=domain)[0] == 0
    assert (vault / f"anatomy/playbooks/{domain}/morning-briefing.md").is_file()


def test_ac5_contributor_mode_leaves_siblings(mechanic, vault, tree):
    d = vault / "anatomy/playbooks/ingest/wearable-pull"
    d.mkdir(parents=True)
    (d / "core.md").write_text("core bytes")
    (d / "other.md").write_text("other bytes")
    before = tree(vault)
    code, out, _ = play(mechanic, "wearable-pull", "ingest", "contributor", contributor="pulse-health-tracking")
    rel = "anatomy/playbooks/ingest/wearable-pull/pulse-health-tracking.md"
    assert code == 0 and out["written"] == [rel]
    after = tree(vault)
    assert {k for k in after if after[k] != before.get(k)} == {rel}
    assert frontmatter.parse((vault / rel).read_text())[0]["event"] == "wearable-pull"


def test_contributor_alongside_core_file_of_same_event(mechanic, vault):
    play(mechanic, "wearable-pull", "ingest")
    assert play(mechanic, "wearable-pull", "ingest", "contributor", contributor="p")[0] == 0
    assert (vault / "anatomy/playbooks/ingest/wearable-pull.md").is_file()
    assert (vault / "anatomy/playbooks/ingest/wearable-pull/p.md").is_file()


@pytest.mark.parametrize("mode,contributor", [("core", None), ("contributor", "plug")])
def test_idempotent_matrix(mechanic, vault, tree, mode, contributor):
    assert play(mechanic, mode=mode, contributor=contributor)[1]["status"] == "ok"
    before = tree(vault)
    code, out, err = play(mechanic, mode=mode, contributor=contributor, fm={**FM, "dispatch_to": ["x"]})
    assert code == 0 and out["status"] == "skipped" and out["written"] == [] and "skipped (idempotent)" in err
    assert tree(vault) == before


@pytest.mark.parametrize("domain", ["Surface", "../x", "", "plan", "ingest/", "/ingest"])
def test_ac7_invalid_domain_no_orphans(mechanic, vault, tree, domain):
    before = tree(vault)
    code, out, _ = play(mechanic, domain=domain)
    assert code == 1 and out["errors"][0] == {"code": "INVALID_DOMAIN", "domain": domain} and tree(vault) == before


@pytest.mark.parametrize(
    "kw",
    [
        {"event": "../x"}, {"event": "/abs"}, {"event": "..\\x"}, {"event": "A"}, {"event": "a b"}, {"event": "é"},
        {"event": "-a"}, {"event": "a" * 65},
        {"mode": "contributor", "contributor": "../x"}, {"mode": "contributor", "contributor": "A"},
    ],
)
def test_ac6_invalid_slug(mechanic, vault, tree, kw):
    before = tree(vault)
    code, out, _ = play(mechanic, **kw)
    assert code == 1 and out["errors"][0]["code"] == "INVALID_SLUG" and tree(vault) == before


@pytest.mark.parametrize(
    "fm",
    [
        {k: v for k, v in FM.items() if k != "triggers"},
        {k: v for k, v in FM.items() if k != "dispatch_to"},
        {k: v for k, v in FM.items() if k != "silence_learned"},
        {**FM, "extra": 1},
        {**FM, "event": "other"},
        {**FM, "triggers": "cron"},
        {**FM, "triggers": [{"cron": "x", "keyword": "y"}]},
        {**FM, "triggers": [{"bogus": "x"}]},
        {**FM, "triggers": [{"cron": 5}]},
        {**FM, "triggers": [{"cron": ""}]},
        {**FM, "triggers": ["cron"]},
        {**FM, "dispatch_to": "skill"},
        {**FM, "dispatch_to": [1]},
        {**FM, "dispatch_to": ["../x"]},
        {**FM, "silence_learned": ["x"]},
        {**FM, "silence_learned": {}},
    ],
)
def test_invalid_frontmatter(mechanic, vault, tree, fm):
    before = tree(vault)
    code, out, _ = play(mechanic, fm=fm)
    assert code == 1 and out["errors"][0]["code"] == "INVALID_FRONTMATTER" and tree(vault) == before


def test_frontmatter_not_json_object(mechanic, vault):
    for raw in ("nope", "[]"):
        code, out, _ = mechanic("forge-playbook", "--event=e", "--domain=act", "--mode=core", f"--frontmatter={raw}")
        assert code == 1 and out["errors"][0]["code"] == "INVALID_FRONTMATTER"


def test_all_trigger_kinds_and_matching_event_accepted(mechanic):
    fm = {**FM, "event": "morning-briefing", "triggers": [{"cron": "x"}, {"keyword": "x"}, {"file": "*.md"}, {"event": "e"}],
          "silence_learned": [{"pattern": "x"}]}
    assert play(mechanic, fm=fm)[0] == 0


@pytest.mark.parametrize("kw", [{"mode": "weird"}, {"mode": "contributor"}, {"mode": "core", "contributor": "p"}])
def test_mode_rules(mechanic, vault, tree, kw):
    before = tree(vault)
    code, out, _ = play(mechanic, **kw)
    assert code == 1 and out["errors"][0]["code"] in ("INVALID_MODE", "INVALID_ARGS") and tree(vault) == before


def test_missing_anatomy_dir(mechanic, vault):
    import shutil

    shutil.rmtree(vault / "anatomy")
    assert play(mechanic)[1]["errors"][0]["code"] == "REGISTRY_NOT_FOUND"


def test_ac8_interrupt_between_tmp_write_and_mv_leaves_nothing_then_retry_succeeds(mechanic, vault, tree, monkeypatch):
    before = tree(vault)
    real = os.replace

    def interrupt(*_):
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "replace", interrupt)
    with pytest.raises(KeyboardInterrupt):
        play(mechanic, "wearable-pull", "ingest", "contributor", contributor="p")
    monkeypatch.setattr(os, "replace", real)
    assert tree(vault) == before and not list(vault.rglob("*.tmp.*"))
    code, out, _ = play(mechanic, "wearable-pull", "ingest", "contributor", contributor="p")
    assert code == 0 and out["status"] == "ok"


def test_failure_keeps_event_dir_when_populated_else_removes(mechanic, vault, tree, monkeypatch):
    d = vault / "anatomy/playbooks/ingest/wearable-pull"
    d.mkdir(parents=True)
    (d / "core.md").write_text("x")
    monkeypatch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(OSError("disk full")))
    code, out, _ = play(mechanic, "wearable-pull", "ingest", "contributor", contributor="p")
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED" and (d / "core.md").read_text() == "x"
    assert [p.name for p in d.iterdir()] == ["core.md"]
    play(mechanic, "fresh-event", "act", "contributor", contributor="p")
    assert not (vault / "anatomy/playbooks/act/fresh-event").exists()


def test_sigterm_between_tmp_write_and_mv_leaves_no_orphans(vault):
    """Real signal injection: the script stalls inside os.replace; SIGTERM must roll back tmp + new dirs."""
    stall = vault.parent / "stall.py"
    stall.write_text(
        "import os, runpy, sys, time\n"
        "real, flag = os.replace, sys.argv[1]\n"
        "def slow(*a):\n"
        "    open(flag, 'w').close()\n"
        "    time.sleep(30)\n"
        "    real(*a)\n"
        "os.replace = slow\n"
        f"sys.argv = [{str(SCRIPT)!r}] + sys.argv[2:]\n"
        f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')\n"
    )
    ready = vault.parent / "ready"
    argv = [sys.executable, str(stall), str(ready), "--event=wearable-pull", "--domain=ingest", "--mode=contributor",
            "--contributor=p", f"--frontmatter={json.dumps(FM)}"]
    proc = subprocess.Popen(argv, env={"GILBERTO_ROOT": str(vault), "PATH": "/usr/bin:/bin"}, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    try:
        for _ in range(100):
            if ready.exists():
                break
            time.sleep(0.05)
        assert ready.exists()
        assert (vault / "anatomy/playbooks/ingest/wearable-pull").is_dir()
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=10)
    finally:
        proc.kill()
    assert not (vault / "anatomy/playbooks").exists()
    assert not list(vault.rglob("*.tmp.*"))


def test_subprocess_smoke_double_run(vault):
    env = {"GILBERTO_ROOT": str(vault), "PATH": "/usr/bin:/bin"}
    argv = [sys.executable, str(SCRIPT), "--event=morning-briefing", "--domain=surface", "--mode=core",
            f"--frontmatter={json.dumps(FM)}"]
    outs = [json.loads(subprocess.run(argv, env=env, capture_output=True, text=True).stdout) for _ in range(2)]
    assert [o["status"] for o in outs] == ["ok", "skipped"]
