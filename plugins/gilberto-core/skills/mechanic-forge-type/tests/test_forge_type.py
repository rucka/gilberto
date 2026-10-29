import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"
SCHEMA = {"required": ["hypothesis", "outcome"], "optional": ["sample_size"]}


def args(**over):
    a = {"name": "experiment", "scope": "pulse", "schema": json.dumps(SCHEMA)}
    a.update(over)
    return [f"--{k}={v}" for k, v in a.items() if v is not None]


def anatomy(vault):
    return (vault / "anatomy/anatomy.md").read_text()


def test_ac4_appends_block_preserving_existing(mechanic, vault):
    before = anatomy(vault)
    code, out, _ = mechanic("forge-type", *args())
    assert code == 0 and out["status"] == "ok" and out["written"] == ["anatomy/anatomy.md"]
    after = anatomy(vault)
    assert (
        "### pulse-experiment\n\n```yaml\nrequired:\n  - hypothesis\n  - outcome\noptional:\n  - sample_size\n```\n"
        in after
    )
    head, tail = before.split("## Relationship levels")
    assert after.startswith(head.rstrip("\n")) and after.endswith("## Relationship levels" + tail)
    assert after.index("pulse-experiment") < after.index("## Relationship levels")
    assert not list(vault.rglob("*.tmp.*"))


def test_ac4_direct_type_and_empty_required(mechanic, vault):
    code, out, _ = mechanic("forge-type", *args(name="person", scope=None, schema='{"required": []}'))
    assert code == 0
    assert "### person\n\n```yaml\nrequired: []\n```\n" in anatomy(vault)


def test_ac5_identical_is_noop(mechanic, vault, tree):
    mechanic("forge-type", *args())
    before = tree(vault)
    reordered = json.dumps({"optional": ["sample_size"], "required": ["outcome", "hypothesis"]})
    code, out, err = mechanic("forge-type", *args(schema=reordered))
    assert code == 0 and out["status"] == "skipped" and out["written"] == []
    assert "skipped (idempotent)" in err and tree(vault) == before


def test_ac5_conflict_without_merge(mechanic, vault, tree):
    mechanic("forge-type", *args())
    before = tree(vault)
    code, out, _ = mechanic("forge-type", *args(schema='{"required": ["hypothesis"]}'))
    assert code == 1
    assert out["errors"] == [
        {
            "code": "TYPE_CONFLICT",
            "type": "pulse-experiment",
            "existing": {"required": ["hypothesis", "outcome"], "optional": ["sample_size"]},
            "supplied": {"required": ["hypothesis"], "optional": []},
        }
    ]
    assert tree(vault) == before


def test_ac5_merge_overlapping(mechanic, vault):
    mechanic("forge-type", *args())
    new = {"required": ["outcome", "result"], "optional": ["sample_size", "notes"]}
    code, out, err = mechanic("forge-type", *args(schema=json.dumps(new)), "--merge")
    assert code == 0 and out["status"] == "ok"
    assert (
        "```yaml\nrequired:\n  - hypothesis\n  - outcome\n  - result\noptional:\n  - sample_size\n  - notes\n```"
        in anatomy(vault)
    )
    assert "+required['result']" in err and "+optional['notes']" in err
    assert anatomy(vault).count("### pulse-experiment") == 1


def test_ac5_merge_disjoint_and_promote(mechanic, vault):
    mechanic("forge-type", *args())
    new = {"required": ["a"], "optional": ["sample_size", "hypothesis"]}
    mechanic("forge-type", *args(schema=json.dumps(new)), "--merge")
    assert "required:\n  - hypothesis\n  - outcome\n  - a\noptional:\n  - sample_size\n```" in anatomy(vault)


def test_merge_without_change_is_noop(mechanic, vault, tree):
    mechanic("forge-type", *args())
    before = tree(vault)
    code, out, _ = mechanic("forge-type", *args(schema='{"required": ["hypothesis"]}'), "--merge")
    assert code == 0 and out["status"] == "skipped" and tree(vault) == before


def test_merge_on_new_type_just_appends(mechanic, vault):
    code, out, _ = mechanic("forge-type", *args(), "--merge")
    assert code == 0 and out["status"] == "ok"


def test_second_type_keeps_first_verbatim(mechanic, vault):
    mechanic("forge-type", *args())
    first = anatomy(vault)
    mechanic("forge-type", *args(name="habit", scope="me"))
    second = anatomy(vault)
    assert first.split("## Relationship levels")[0].rstrip("\n") in second
    assert second.index("### pulse-experiment") < second.index("### me-habit") < second.index("## Relationship")


@pytest.mark.parametrize("bad", ["../x", "..\\x", "/abs", "Upper", "a b", "é", "-x", "a" * 65, "x\n"])
def test_ac6_invalid_slug(mechanic, vault, tree, bad):
    before = tree(vault)
    code, out, _ = mechanic("forge-type", *args(name=bad))
    assert code == 1 and out["errors"] == [{"code": "INVALID_SLUG", "input": bad}]
    code, out, _ = mechanic("forge-type", *args(scope=bad))
    assert code == 1 and out["errors"] == [{"code": "INVALID_SLUG", "input": bad}]
    assert tree(vault) == before


@pytest.mark.parametrize("kw", [{"scope": "ghost"}, {"scope": None}, {"scope": None, "name": "company-x"}])
def test_invalid_scope(mechanic, vault, tree, kw):
    before = tree(vault)
    code, out, _ = mechanic("forge-type", *args(**kw))
    assert code == 1 and out["errors"][0]["code"] == "INVALID_SCOPE"
    assert tree(vault) == before


@pytest.mark.parametrize(
    "schema",
    [
        "not json",
        "[]",
        "{}",
        '{"optional": ["a"]}',
        '{"required": "a"}',
        '{"required": [], "optional": [1]}',
        '{"required": [""]}',
        '{"required": [], "extra": []}',
    ],
)
def test_invalid_schema(mechanic, vault, tree, schema):
    before = tree(vault)
    code, out, _ = mechanic("forge-type", *args(schema=schema))
    assert code == 1 and out["errors"][0]["code"] == "INVALID_SCHEMA" and out["errors"][0]["input"] == schema
    assert tree(vault) == before


def test_registry_without_types_section(mechanic, vault, tree):
    (vault / "anatomy/anatomy.md").write_text("# Anatomy\n")
    before = tree(vault)
    code, out, _ = mechanic("forge-type", *args())
    assert code == 1 and out["errors"][0]["code"] == "REGISTRY_NOT_FOUND"
    assert tree(vault) == before


def test_missing_arg(mechanic):
    code, out, _ = mechanic("forge-type", "--name=x")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_ARGS"


def test_write_failure_leaves_registry_intact(mechanic, vault, tree, monkeypatch):
    before = tree(vault)

    def boom(a, b):
        raise OSError(5, "EIO")

    monkeypatch.setattr(os, "replace", boom)
    code, out, _ = mechanic("forge-type", *args())
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED"
    assert tree(vault) == before


def test_subprocess_smoke_twice(vault):
    env = {**os.environ, "GILBERTO_ROOT": str(vault)}
    cmd = [sys.executable, str(SCRIPT), *args()]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert p.returncode == 0 and json.loads(p.stdout)["status"] == "ok"
    p2 = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert json.loads(p2.stdout)["status"] == "skipped"
