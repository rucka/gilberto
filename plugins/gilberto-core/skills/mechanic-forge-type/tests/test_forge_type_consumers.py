"""Review r0-2/r0-3/r0-4: schema keys, hand-written blocks, schema consumed by vault-new."""
import json

import pytest

SCHEMA = {"required": ["hypothesis", "outcome"], "optional": ["sample_size"]}


def forge(mechanic, schema=SCHEMA, *extra):
    return mechanic("forge-type", "--name=experiment", "--scope=pulse", f"--schema={json.dumps(schema)}", *extra)


def hand_write(vault, block):
    p = vault / "anatomy/anatomy.md"
    p.write_text(p.read_text().replace("## Relationship levels", f"{block}\n## Relationship levels"))


def new_note(mechanic, vault, fm):
    tpl = vault / "anatomy/templates/pulse/exp"
    tpl.mkdir(parents=True, exist_ok=True)
    (tpl / "exp.md").write_text("---\ntype: pulse-experiment\ntopics: []\n---\n\n# x\n")
    return mechanic("new", "--pillar=pulse", "--template=exp", "--slug=e1", f"--frontmatter={json.dumps(fm)}")


# r0-4


def test_vault_new_rejects_missing_required_from_forged_schema(mechanic, vault):
    forge(mechanic)
    code, out, _ = new_note(mechanic, vault, {})
    assert code == 1 and out["errors"][0]["code"] == "INVALID_FRONTMATTER"
    assert out["errors"][0]["diff"] == {"missing": ["hypothesis", "outcome"], "unknown": []}
    assert not (vault / "pulse/e1").exists()


def test_vault_new_rejects_unknown_key_from_forged_schema(mechanic, vault):
    forge(mechanic)
    code, out, _ = new_note(mechanic, vault, {"hypothesis": "h", "outcome": "o", "bogus": 1})
    assert code == 1 and out["errors"][0]["diff"] == {"missing": [], "unknown": ["bogus"]}


def test_vault_new_accepts_conforming_note(mechanic, vault):
    forge(mechanic)
    code, out, _ = new_note(mechanic, vault, {"hypothesis": "h", "outcome": "o", "sample_size": 3})
    assert code == 0 and "pulse/e1/e1.md" in out["written"]


# r0-3

HAND = {
    "zero-indent": "### pulse-experiment\n\n```yaml\nrequired:\n- hypothesis\n- outcome\n```\n",
    "quoted-flow": '### pulse-experiment\n\n```yaml\nrequired: ["hypothesis", "outcome"]\n```\n',
    "flow-comment": "### pulse-experiment\n\n```yaml\nrequired: [hypothesis, outcome] # c\n```\n",
    "unquoted-flow": "### pulse-experiment\n\n```yaml\nrequired: [hypothesis, outcome]\n```\n",
    "no-blank-line": "### pulse-experiment\n```yaml\nrequired:\n  - hypothesis\n  - outcome\n```\n",
    "quoted-block": "### pulse-experiment\n\n```yaml\nrequired:\n  - 'hypothesis'\n  - \"outcome\"\n```\n",
}


@pytest.mark.parametrize("block", HAND.values(), ids=HAND.keys())
def test_hand_written_block_merge_keeps_existing(mechanic, vault, block):
    hand_write(vault, block)
    code, _, _ = forge(mechanic, {"required": ["result"]}, "--merge")
    assert code == 0
    text = (vault / "anatomy/anatomy.md").read_text()
    assert text.count("### pulse-experiment") == 1
    assert "required:\n  - hypothesis\n  - outcome\n  - result\n" in text


@pytest.mark.parametrize("block", HAND.values(), ids=HAND.keys())
def test_hand_written_block_identical_rerun_noop(mechanic, vault, tree, block):
    hand_write(vault, block)
    before = tree(vault)
    code, out, _ = forge(mechanic, {"required": ["outcome", "hypothesis"]})
    assert code == 0 and out["status"] == "skipped" and tree(vault) == before


@pytest.mark.parametrize("block", HAND.values(), ids=HAND.keys())
def test_hand_written_block_conflict_reports_real_existing(mechanic, vault, block):
    hand_write(vault, block)
    code, out, _ = forge(mechanic, {"required": ["x"]})
    assert code == 1 and out["errors"][0]["existing"] == {"required": ["hypothesis", "outcome"], "optional": []}


@pytest.mark.parametrize("block", HAND.values(), ids=HAND.keys())
def test_hand_written_block_enforced_by_vault_new(mechanic, vault, block):
    hand_write(vault, block)
    code, out, _ = new_note(mechanic, vault, {"bogus": 1})
    assert code == 1 and out["errors"][0]["diff"] == {"missing": ["hypothesis", "outcome"], "unknown": ["bogus"]}


BROKEN = {
    "no-fence": "### pulse-experiment\n\nrequired: [a]\n",
    "unclosed-flow": "### pulse-experiment\n\n```yaml\nrequired: [a, b\n```\n",
    "unknown-key": "### pulse-experiment\n\n```yaml\nrequired: []\nextra: [a]\n```\n",
    "scalar": "### pulse-experiment\n\n```yaml\nrequired: a\n```\n",
    "no-required": "### pulse-experiment\n\n```yaml\noptional: [a]\n```\n",
}


@pytest.mark.parametrize("block", BROKEN.values(), ids=BROKEN.keys())
def test_unparseable_block_is_typed_error(mechanic, vault, tree, block):
    hand_write(vault, block)
    before = tree(vault)
    for extra in ((), ("--merge",)):
        code, out, _ = forge(mechanic, SCHEMA, *extra)
        assert code == 1 and out["errors"][0]["code"] == "INVALID_TYPE_BLOCK"
        assert out["errors"][0]["type"] == "pulse-experiment"
    snap = tree(vault)
    code, out, _ = new_note(mechanic, vault, {})
    assert code == 1 and out["errors"][0]["code"] == "INVALID_TYPE_BLOCK"
    assert snap == before and not (vault / "pulse/e1").exists()


# r0-2


@pytest.mark.parametrize("key", ["a\n## Hacked", "a```", "a b", "-a", "a:b", "#a", "a" * 65, "é", "A"])
def test_schema_keys_must_be_identifiers(mechanic, vault, tree, key):
    before = tree(vault)
    for k in ("required", "optional"):
        code, out, _ = forge(mechanic, {"required": [], k: [key]})
        assert code == 1 and out["errors"][0]["code"] == "INVALID_SCHEMA"
    assert tree(vault) == before


def test_schema_keys_accept_snake_and_kebab(mechanic, vault):
    code, _, _ = forge(mechanic, {"required": ["sample_size", "ab-test", "x1"]})
    assert code == 0
