from test_remediation_r2 import HEAD, _utf8_page


def test_valid_undeclared_utf8_control(mod):
    out = mod._decode(_utf8_page(), "text/html")
    assert "città" in out and "�" not in out


def test_undeclared_cp1252_control(mod):
    raw = (HEAD + "è" * 50).encode("cp1252")
    out = mod._decode(raw, "text/html")
    assert "città" in out and "�" not in out


def test_undeclared_cp1252_single_non_ascii_byte_control(mod):
    raw = (HEAD + "ciao</p></body></html>").encode("cp1252")
    out = mod._decode(raw, "text/html")
    assert "città" in out and "�" not in out
