import json

import pytest
from archive_helpers import FM, args

LINE_SEPS = ["\n", "\r", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", " ", " "]
STRIP_WS = ["\t", " ", "\x1f", "\xa0", " ", " ", " ", " ", " ", "　"]
BAD_KEYS = [
    "x\n---\ninjected", "a b", "a:b", "", "-x", "#x", ":a", "a:", "a\tb", "a\x1fb",
    *[f"a{c}b" for c in LINE_SEPS],
    *[f"{c}a" for c in STRIP_WS],
    *[f"a{c}" for c in STRIP_WS],
]
EXISTING_KEYS = ["a b", "a b", "a\x0bb", "a b", "a ", "a\t"]


@pytest.mark.parametrize("key", BAD_KEYS, ids=repr)
def test_invalid_frontmatter_key_rejected_nothing_written(archive, avault, snap, key):
    before = snap(avault)
    code, out, _ = archive(*args(frontmatter=json.dumps({**FM, key: 1})))
    assert code == 1 and out["errors"][0]["code"] == "INVALID_FRONTMATTER"
    assert snap(avault) == before


@pytest.mark.parametrize("key", EXISTING_KEYS, ids=repr)
def test_invalid_key_with_existing_note_rejected_not_idempotent(archive, avault, snap, key):
    code, out, _ = archive(*args())
    assert code == 0, out
    note = avault / "intelligence/health/acme/e1.md"
    assert note.is_file()
    before, text = snap(avault), note.read_bytes()
    code, out, _ = archive(*args(frontmatter=json.dumps({**FM, key: 1})))
    assert code == 1 and out["errors"][0]["code"] == "INVALID_FRONTMATTER"
    assert note.read_bytes() == text and snap(avault) == before
