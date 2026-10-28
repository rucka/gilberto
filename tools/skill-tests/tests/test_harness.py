import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run-tests.sh"

_PASS = "def test_ok():\n    pass\n"


def test_synthetic_vault_shape(synthetic_vault):
    assert synthetic_vault.is_dir()
    for d in ("inbox", "notes", "projects", "journal"):
        assert (synthetic_vault / d).is_dir()
    assert (synthetic_vault / "README.md").is_file()


def test_runner_maps_no_tests_collected_to_zero(tmp_path):
    r = subprocess.run(["bash", str(SCRIPT), str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_runner_propagates_failure(tmp_path):
    (tmp_path / "test_fail.py").write_text("def test_x():\n    assert False\n")
    r = subprocess.run(
        ["bash", str(SCRIPT), "-p", "no:cacheprovider", "--no-cov", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1
    assert "assert False" in r.stdout


def test_runner_missing_uv_hints(tmp_path):
    bash = subprocess.run(["bash", "-c", "command -v bash"], capture_output=True, text=True).stdout.strip()
    r = subprocess.run([bash, str(SCRIPT)], env={"PATH": str(tmp_path)}, capture_output=True, text=True)
    assert r.returncode != 0
    assert "uv" in r.stderr and "Install" in r.stderr


def test_plugins_skill_tests_discovered(tmp_path, run_harness):
    r = run_harness(tmp_path, [("a", "s1", {"tests/test_skill.py": _PASS})])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 passed" in r.stdout


def test_coverage_xml_written_under_coverage_dir(tmp_path, run_harness):
    r = run_harness(tmp_path, [("a", "s1", {"tests/test_skill.py": _PASS})])
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "tools" / "skill-tests" / "coverage" / "coverage.xml").is_file()
