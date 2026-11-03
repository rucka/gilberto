import json

from archive_helpers import FM, args


def test_simple_identifier_keys_still_accepted(archive, avault):
    code, out, _ = archive(*args(frontmatter=json.dumps({**FM, "my-key_2": 1, "Tags": ["x"]})))
    assert code == 0 and out["status"] == "ok"
    text = (avault / "intelligence/health/acme/e1.md").read_text()
    assert 'my-key_2: 1' in text and text.count("\n---\n") == 1
