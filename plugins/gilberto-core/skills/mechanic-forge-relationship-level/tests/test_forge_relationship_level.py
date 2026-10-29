import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"
ANATOMY = "anatomy/anatomy.md"
CRIT = "met at least once; opt-in recall"


def level(mechanic, name="associate", criteria=CRIT, **kw):
    return mechanic("forge-relationship-level", f"--name={name}", f"--criteria={criteria}", **kw)


def test_ac3_append_to_empty_section(mechanic, vault):
    f = vault / ANATOMY
    before = f.read_text()
    code, out, _ = level(mechanic)
    assert code == 0 and out == {"status": "ok", "written": [ANATOMY], "skipped": [], "errors": []}
    assert f.read_text() == before + f"\n- associate — {CRIT}\n"


def test_ac3_stable_order_and_adjacent_sections_byte_identical(mechanic, vault):
    f = vault / ANATOMY
    f.write_text(f.read_text() + "\n- friend — close\n\n## After\n\nkeep me\n")
    before = f.read_text()
    level(mechanic)
    level(mechanic, "colleague", "works together")
    text = f.read_text()
    assert text == before.replace("- friend — close\n", f"- friend — close\n- associate — {CRIT}\n- colleague — works together\n")


def test_ac3_empty_section_before_next_heading(mechanic, vault):
    f = vault / ANATOMY
    f.write_text("# A\n\n## Relationship levels\n\n## Next\n\nx\n")
    level(mechanic)
    assert f.read_text() == f"# A\n\n## Relationship levels\n\n- associate — {CRIT}\n\n## Next\n\nx\n"


def test_table_section_gets_table_row(mechanic, vault):
    f = vault / ANATOMY
    f.write_text("## Relationship levels\n\n| Level | Description |\n| ----- | ----------- |\n| friend | close |\n\n## After\n")
    level(mechanic, criteria="a | b")
    assert f.read_text() == (
        "## Relationship levels\n\n| Level | Description |\n| ----- | ----------- |\n| friend | close |\n| associate | a \\| b |\n\n## After\n"
    )
    assert level(mechanic)[1]["status"] == "skipped"


def test_header_only_table(mechanic, vault):
    f = vault / ANATOMY
    f.write_text("## Relationship levels\n\n| Level | Description |\n| ----- | ----------- |\n")
    level(mechanic)
    assert f.read_text().endswith("| ----- | ----------- |\n| associate | " + CRIT + " |\n")
    assert level(mechanic, "level", "x")[1]["status"] == "ok"


def test_idempotent_by_name(mechanic, vault, tree):
    level(mechanic)
    before = tree(vault)
    code, out, err = level(mechanic, criteria="different criteria")
    assert code == 0 and out["status"] == "skipped" and out["written"] == [] and "skipped (idempotent)" in err
    assert tree(vault) == before


@pytest.mark.parametrize(
    "name,criteria,code_",
    [
        ("../x", CRIT, "INVALID_SLUG"),
        ("/abs", CRIT, "INVALID_SLUG"),
        ("..\\x", CRIT, "INVALID_SLUG"),
        ("Assoc", CRIT, "INVALID_SLUG"),
        ("a b", CRIT, "INVALID_SLUG"),
        ("àb", CRIT, "INVALID_SLUG"),
        ("-a", CRIT, "INVALID_SLUG"),
        ("a" * 65, CRIT, "INVALID_SLUG"),
        ("ok", "  \n ", "INVALID_CRITERIA"),
    ],
)
def test_rejects_and_writes_nothing(mechanic, vault, tree, name, criteria, code_):
    before = tree(vault)
    code, out, _ = level(mechanic, name, criteria)
    assert code == 1 and out["errors"][0]["code"] == code_ and tree(vault) == before


def test_missing_section_and_file(mechanic, vault, tree):
    (vault / ANATOMY).write_text("# nothing\n")
    code, out, _ = level(mechanic)
    assert code == 1 and out["errors"][0]["code"] == "REGISTRY_NOT_FOUND"
    (vault / ANATOMY).unlink()
    assert level(mechanic)[1]["errors"][0]["code"] == "REGISTRY_NOT_FOUND"


def test_write_failure_rolls_back(mechanic, vault, tree, monkeypatch):
    import os

    before = tree(vault)
    monkeypatch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(OSError("disk full")))
    code, out, _ = level(mechanic)
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED" and tree(vault) == before


def test_subprocess_smoke_double_run(vault):
    env = {"GILBERTO_ROOT": str(vault), "PATH": "/usr/bin:/bin"}
    outs = [json.loads(subprocess.run([sys.executable, str(SCRIPT), "--name=associate", f"--criteria={CRIT}"], env=env,
                                      capture_output=True, text=True).stdout) for _ in range(2)]
    assert [o["status"] for o in outs] == ["ok", "skipped"]
