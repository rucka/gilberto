import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SEED = HERE.parents[3] / "packages" / "vault-bootstrap" / "seed" / "anatomy" / "preferences.md"
spec = importlib.util.spec_from_file_location("ingest_seed_threshold_control_script", HERE / "script.py")
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


def seed_with(root, value):
    (root / "anatomy").mkdir()
    (root / "anatomy" / "preferences.md").write_text(SEED.read_text().replace("0.7", value))


def test_seed_unedited_is_default(tmp_path):
    seed_with(tmp_path, "0.7")
    assert script._threshold(str(tmp_path), None) == 0.7


def test_seed_out_of_range_falls_back_to_default(tmp_path):
    seed_with(tmp_path, "1.5")
    assert script._threshold(str(tmp_path), None) == 0.7
