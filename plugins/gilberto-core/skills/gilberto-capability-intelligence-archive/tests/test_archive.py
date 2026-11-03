import json
import re
from datetime import date

import pytest
from archive_helpers import args

TODAY = date.today().isoformat()


def test_ac1_places_entity(archive, avault):
    code, out, _ = archive(*args(frontmatter=json.dumps({"type": "intelligence-note", "tags": ["x"]})))
    assert code == 0 and out["status"] == "ok" and out["errors"] == []
    text = (avault / "intelligence/health/acme/e1.md").read_text()
    assert text.startswith(
        f'---\ntype: "intelligence-note"\ntopics: ["health"]\ntags: ["x"]\ncreated: "{TODAY}"\nupdated: "{TODAY}"\n---\n'
    )
    assert "# {{title}}" in text and "intelligence/health/acme/e1.md" in out["written"]


def test_ac1_tags_optional(archive, avault):
    archive(*args())
    assert "tags" not in (avault / "intelligence/health/acme/e1.md").read_text()


def test_ac1_supplied_topics_win(archive, avault):
    archive(*args(frontmatter=json.dumps({"type": "intelligence-note", "topics": ["health", "x"]})))
    assert 'topics: ["health", "x"]' in (avault / "intelligence/health/acme/e1.md").read_text()


def test_ac2_idempotent(archive, avault, snap):
    archive(*args())
    before = snap(avault)
    code, out, err = archive(*args())
    assert code == 0 and out["status"] == "skipped" and out["written"] == []
    assert out["skipped"] == ["intelligence/health/acme/e1.md"] and "skipped (idempotent)" in err
    assert snap(avault) == before


def test_idempotent_ignores_dates(archive, avault, snap):
    archive(*args())
    note = avault / "intelligence/health/acme/e1.md"
    note.write_text(re.sub(r'created: ".*"', 'created: "2000-01-01"', note.read_text()))
    before = snap(avault)
    code, out, _ = archive(*args())
    assert code == 0 and out["status"] == "skipped" and snap(avault) == before


@pytest.mark.parametrize("over", [{"frontmatter": json.dumps({"type": "intelligence-note", "tags": ["y"]})}])
def test_conflict_different_frontmatter(archive, avault, snap, over):
    archive(*args())
    before = snap(avault)
    code, out, _ = archive(*args(**over))
    assert code == 1 and out["errors"] == [{"code": "CONFLICT", "path": "intelligence/health/acme/e1.md"}]
    assert snap(avault) == before


def test_conflict_edited_body(archive, avault, snap):
    archive(*args())
    note = avault / "intelligence/health/acme/e1.md"
    note.write_text(note.read_text() + "edited\n")
    before = snap(avault)
    code, out, _ = archive(*args())
    assert code == 1 and out["errors"][0]["code"] == "CONFLICT" and snap(avault) == before


@pytest.mark.parametrize("field", ["topic", "source", "entity", "template"])
@pytest.mark.parametrize("bad", ["../x", "Up", "a b", "-x", "a" * 65, "x\n", "_uncategorized", "a/b"])
def test_invalid_slugs(archive, avault, snap, field, bad):
    before = snap(avault)
    code, out, _ = archive(*args(**{field: bad}))
    assert code == 1 and out["errors"][0]["code"] == "INVALID_SLUG" and snap(avault) == before


@pytest.mark.parametrize(
    "fm,code_",
    [("[]", "INVALID_FRONTMATTER"), ("nope", "INVALID_FRONTMATTER"), (json.dumps({"type": "bogus"}), "INVALID_FRONTMATTER")],
)
def test_invalid_frontmatter(archive, avault, snap, fm, code_):
    before = snap(avault)
    code, out, _ = archive(*args(frontmatter=fm))
    assert code == 1 and out["errors"][0]["code"] == code_ and snap(avault) == before


def test_missing_template(archive, avault, snap):
    before = snap(avault)
    code, out, _ = archive(*args(template="nope"))
    assert code == 1 and out["errors"][0]["code"] == "TEMPLATE_NOT_FOUND" and snap(avault) == before


def test_missing_args(archive):
    code, out, _ = archive("--topic=health")
    assert code == 1 and out["errors"][0]["code"] == "INVALID_ARGS"


def test_write_failure_rolls_back(archive, avault, snap, monkeypatch):
    import _lib.atomic_write as aw

    before = snap(avault)
    monkeypatch.setattr(aw, "atomic_write", lambda p, d: (_ for _ in ()).throw(OSError("full")))
    code, out, _ = archive(*args())
    assert code == 1 and out["errors"][0]["code"] == "WRITE_FAILED" and snap(avault) == before


# AC3 / T-3
def test_ac3_unknown_topic_uncategorized(archive, avault):
    code, out, err = archive(*args(topic="newtopic"))
    assert code == 0 and (avault / "intelligence/_uncategorized/acme/e1.md").is_file()
    assert not (avault / "intelligence/newtopic").exists()
    assert "_uncategorized" in err and 'topics: []' in (avault / "intelligence/_uncategorized/acme/e1.md").read_text()


def test_ac3_unknown_topic_confirmed(archive, avault):
    code, out, _ = archive(*args(topic="newtopic"), "--confirm-topic")
    assert code == 0 and (avault / "intelligence/newtopic/acme/e1.md").is_file()
    assert 'topics: ["newtopic"]' in (avault / "intelligence/newtopic/acme/e1.md").read_text()


def test_confirm_topic_noop_on_known(archive, avault):
    archive(*args(), "--confirm-topic")
    assert (avault / "intelligence/health/acme/e1.md").is_file()


def test_missing_topics_registry_is_unknown(archive, avault):
    (avault / "anatomy/topics.md").unlink()
    code, _, _ = archive(*args())
    assert code == 0 and (avault / "intelligence/_uncategorized/acme/e1.md").is_file()


def test_unknown_source_needs_confirm(archive, avault, snap):
    before = snap(avault)
    code, out, _ = archive(*args(source="newsrc"))
    assert code == 1 and out["errors"] == [{"code": "SOURCE_UNCONFIRMED", "source": "newsrc"}]
    assert snap(avault) == before


def test_unknown_source_confirmed(archive, avault):
    code, out, _ = archive(*args(source="newsrc"), "--confirm-source")
    assert code == 0 and (avault / "intelligence/health/newsrc/e1.md").is_file()


def test_source_known_by_existing_dir(archive, avault):
    (avault / "intelligence/health/dirsrc").mkdir(parents=True)
    code, _, _ = archive(*args(source="dirsrc"))
    assert code == 0


def test_uncategorized_source_still_confirmed(archive, avault, snap):
    before = snap(avault)
    code, out, _ = archive(*args(topic="newtopic", source="newsrc"))
    assert code == 1 and out["errors"][0]["code"] == "SOURCE_UNCONFIRMED" and snap(avault) == before
