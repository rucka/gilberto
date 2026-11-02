import importlib.util
import json
import os
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ingest_confidence_script", HERE / "script.py")
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


@pytest.mark.parametrize("flag", ["--confidence=nan", "--confidence=-0.1", "--confidence=1.5", "--threshold=nan", "--threshold=inf"])
def test_out_of_range_confidence_or_threshold_rejected(tmp_path, capsys, flag):
    root = tmp_path / "vault"
    (root / "_ingest").mkdir(parents=True)
    (root / "me").mkdir()
    env = {"GILBERTO_ROOT": str(root), "GILBERTO_SKILLS_DIR": str(tmp_path / "plugins"), "HOME": str(tmp_path)}
    p = root / "_ingest" / "a.pdf"
    p.write_bytes(b"%PDF")
    t = time.time() - 60
    os.utime(p, (t, t))
    key = flag.split("=")[0]
    argv = [x for x in ["apply", "--file=a.pdf", "--pillar=me", "--confidence=0.9"] if not x.startswith(key)] + [flag]
    capsys.readouterr()
    code = script.main(argv, env)
    out = json.loads(capsys.readouterr().out)
    assert code == 1 and out["errors"][0]["code"] == "INVALID_ARGS"
    assert p.exists() and not (root / "_ingest" / "a.pdf.error.md").exists()
