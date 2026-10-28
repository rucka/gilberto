import pytest

from _lib import validate
from _lib.result import MechanicError


@pytest.mark.parametrize("bad", ["../x", "..\\x", "/abs", "Upper", "a b", "ünï", "-lead", "a" * 65, "", "a/b"])
def test_slug_rejects(bad):
    with pytest.raises(MechanicError) as e:
        validate.slug(bad)
    assert e.value.as_dict() == {"code": "INVALID_SLUG", "input": bad}


def test_slug_rejects_trailing_newline():
    with pytest.raises(MechanicError) as e:
        validate.slug("alpha\n")
    assert e.value.as_dict() == {"code": "INVALID_SLUG", "input": "alpha\n"}


def test_rel_path_rejects_trailing_newline(vault):
    for raw, suffix in (("projects/alpha\n", ""), ("projects/alpha\n.md", ".md"), ("projects\n/alpha", "")):
        with pytest.raises(MechanicError) as e:
            validate.rel_path(str(vault), raw, suffix)
        assert e.value.as_dict() == {"code": "INVALID_SLUG", "input": raw}


def test_frontmatter_rejects_trailing_newline_type(vault):
    fm = {"type": "projects-index\n", "topics": [], "created": "2020-01-01", "updated": "2020-01-01"}
    with pytest.raises(MechanicError) as e:
        validate.frontmatter(str(vault), fm)
    assert e.value.as_dict() == {"code": "INVALID_FRONTMATTER", "type": "projects-index\n", "reason": "unknown type scope"}


def test_slug_accepts():
    assert validate.slug("a" * 64) == "a" * 64
    assert validate.slug("alpha-1") == "alpha-1"


def test_pillar_fixed_set_and_presence(vault):
    assert validate.pillar(str(vault), "network") == "network"
    for bad in ("ghost", "anatomy"):
        with pytest.raises(MechanicError) as e:
            validate.pillar(str(vault), bad)
        assert e.value.as_dict() == {"code": "PILLAR_NOT_FOUND", "pillar": bad}
    (vault / "me").rmdir()
    with pytest.raises(MechanicError):
        validate.pillar(str(vault), "me")


def test_rel_path(vault):
    root = str(vault)
    assert validate.rel_path(root, "projects/alpha.md", ".md") == ["projects", "alpha"]
    assert validate.rel_path(root, "projects/alpha") == ["projects", "alpha"]
    for bad in ("../a/b", "/projects/a", "projects", "projects/A", "projects/a.md"):
        with pytest.raises(MechanicError) as e:
            validate.rel_path(root, bad)
        assert e.value.code == "INVALID_SLUG"
    with pytest.raises(MechanicError) as e:
        validate.rel_path(root, "projects/alpha", ".md")
    assert e.value.code == "INVALID_SLUG"
    with pytest.raises(MechanicError) as e:
        validate.rel_path(root, "ghost/alpha")
    assert e.value.code == "PILLAR_NOT_FOUND"


GOOD = {"type": "project-index", "topics": ["g"], "created": "d", "updated": "d", "status": "active"}


def test_frontmatter_ok(vault):
    assert validate.frontmatter(str(vault), GOOD) == GOOD
    assert validate.frontmatter(str(vault), {**GOOD, "type": "person"})
    assert validate.frontmatter(str(vault), {**GOOD, "type": "pulse-health", "status": 1})  # unregistered: no schema


@pytest.mark.parametrize(
    "fm",
    [
        {"type": "project-index"},
        {**GOOD, "type": "bogus-thing"},
        {**GOOD, "type": "projects-"},
        {**GOOD, "topics": "x"},
    ],
)
def test_frontmatter_rejects(vault, fm):
    with pytest.raises(MechanicError) as e:
        validate.frontmatter(str(vault), fm)
    assert e.value.code == "INVALID_FRONTMATTER"


def test_frontmatter_anatomy_diff(vault):
    no_status = {k: v for k, v in GOOD.items() if k != "status"}
    with pytest.raises(MechanicError) as e:
        validate.frontmatter(str(vault), {**no_status, "extra": 1})
    assert e.value.extra["diff"] == {"missing": ["status"], "unknown": ["extra"]}


def test_frontmatter_no_anatomy(vault):
    (vault / "anatomy" / "anatomy.md").unlink()
    assert validate.frontmatter(str(vault), {**GOOD, "extra": 1})
