_PASS = "def test_ok():\n    pass\n"


def test_same_basename_skill_tests_both_collected(tmp_path, run_harness):
    r = run_harness(
        tmp_path,
        [("a", "s1", {"tests/test_skill.py": _PASS}), ("b", "s2", {"tests/test_skill.py": _PASS})],
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "2 passed" in r.stdout


def test_coverage_measures_skill_script(tmp_path, run_harness):
    test = (
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))\n"
        "import foo\n"
        "def test_foo():\n    assert foo.add(1, 2) == 3\n"
    )
    r = run_harness(
        tmp_path,
        [("a", "s1", {"scripts/foo.py": "def add(a, b):\n    return a + b\n", "tests/test_skill.py": test})],
    )
    assert r.returncode == 0, r.stdout + r.stderr
    xml = (tmp_path / "tools" / "skill-tests" / "coverage" / "coverage.xml").read_text()
    assert "foo.py" in xml
