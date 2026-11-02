HEAD = "<html><head><title>La città</title></head><body><p>"


def _utf8_page(tail="è" * 2000):
    return (HEAD + tail).encode("utf-8")


def test_truncated_undeclared_utf8_keeps_accents(mod):
    out = mod._decode(_utf8_page()[:-1], "text/html")
    assert "<title>La città</title>" in out and "Ã" not in out


def test_truncated_undeclared_utf8_three_byte_char(mod):
    out = mod._decode((HEAD + "€" * 1000).encode("utf-8")[:-1], "text/html")
    assert "città" in out and "Ã" not in out


def test_single_invalid_byte_midstream_keeps_accents(mod):
    raw = _utf8_page("è" * 1000) + b"\xff" + "è".encode("utf-8") * 1000
    out = mod._decode(raw, "text/html")
    assert "città" in out and "Ã" not in out
