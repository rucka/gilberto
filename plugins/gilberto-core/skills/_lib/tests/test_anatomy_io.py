import pytest

from _lib import anatomy_io
from _lib.result import MechanicError

DOC = "# A\n\n## Types\n\n| Type | Folder |\n| ---- | ------ |\n| x | y |\n\n## Relationship levels\n\nend\n"
SCHEMA = {"required": ["a", "b"], "optional": ["c"]}


def test_has_topic_ignores_header_and_matches_first_cell():
    t = "| Topic | Description |\n| ----- | ----- |\n| sleep | Topic |\n"
    assert anatomy_io.has_topic(t, "sleep") and not anatomy_io.has_topic(t, "Topic")
    assert not anatomy_io.has_topic(t, "Description") and not anatomy_io.has_topic("", "x")


def test_append_topic_inserts_after_table_keeps_rest_byte_stable():
    t = "intro\n\n| Topic | D |\n| - | - |\n| a | |\n\ntail\n"
    new = anatomy_io.append_topic(t, "b", "x|y\nz")
    assert new == "intro\n\n| Topic | D |\n| - | - |\n| a | |\n| b | x\\|y z |\n\ntail\n"
    assert anatomy_io.append_topic(t, "b", "") .count("| b |  |") == 1


@pytest.mark.parametrize("text", ["", "prose\n", "prose\n\n", "prose"])
def test_append_topic_without_table_creates_one(text):
    new = anatomy_io.append_topic(text, "a")
    assert new.startswith(text) and new.endswith("| Topic | Description |\n| ----- | ----------- |\n| a |  |\n")
    assert anatomy_io.has_topic(new, "a")


def test_append_type_roundtrip_preserves_surroundings():
    new = anatomy_io.append_type(DOC, "pulse-x", SCHEMA)
    assert new.startswith(DOC.split("## Relationship")[0].rstrip("\n"))
    assert new.endswith("## Relationship levels\n\nend\n")
    assert anatomy_io.get_type(new, "pulse-x") == SCHEMA
    assert anatomy_io.get_type(new, "pulse-y") is None
    assert "```yaml\nrequired:\n  - a\n  - b\noptional:\n  - c\n```" in new


def test_append_type_empty_required_and_empty_section():
    new = anatomy_io.append_type("## Types\n", "me-z", {"required": [], "optional": []})
    assert new == "## Types\n\n### me-z\n\n```yaml\nrequired: []\n```\n"
    assert anatomy_io.get_type(new, "me-z") == {"required": [], "optional": []}


def test_append_type_at_eof_without_trailing_newline():
    new = anatomy_io.append_type("## Types\ntext", "me-z", SCHEMA)
    assert new.startswith("## Types\ntext\n\n### me-z") and anatomy_io.get_type(new, "me-z") == SCHEMA


def test_merge_union_keeps_order_and_promotes():
    t = anatomy_io.append_type(DOC, "pulse-x", SCHEMA)
    new, added = anatomy_io.merge_type(t, "pulse-x", {"required": ["z", "a", "c"], "optional": ["q", "b"]})
    assert anatomy_io.get_type(new, "pulse-x") == {"required": ["a", "b", "z", "c"], "optional": ["q"]}
    assert added == {"required": ["z", "c"], "optional": ["q"]}
    assert new.endswith("## Relationship levels\n\nend\n")


def test_missing_section_raises():
    with pytest.raises(MechanicError) as e:
        anatomy_io.get_type("# nothing\n", "x")
    assert e.value.code == "REGISTRY_NOT_FOUND"


def test_read_missing_file(tmp_path):
    with pytest.raises(MechanicError) as e:
        anatomy_io.read(str(tmp_path), "anatomy/topics.md")
    assert e.value.as_dict() == {"code": "REGISTRY_NOT_FOUND", "file": "anatomy/topics.md"}


def test_render_placeholders():
    assert anatomy_io.render("{{SLUG}}|{{TITLE}}|{{DATE}}", "s", "T", "d") == "s|T|d"
