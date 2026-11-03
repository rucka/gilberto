import json
import os
import subprocess
import sys

from archive_helpers import SCRIPT, SKILLS, args


def test_ingest_dispatches_by_capability_name():
    assert SCRIPT.parent.name == "gilberto-capability-intelligence-archive"
    assert 'f"gilberto-capability-{pillar}-archive"' in (SKILLS / "gilberto-process-ingest/script.py").read_text()


def test_result_json_contract_subprocess_smoke(avault):
    env = {**os.environ, "GILBERTO_ROOT": str(avault)}

    def run(*a):
        return subprocess.run([sys.executable, str(SCRIPT), *a], capture_output=True, text=True, env=env)

    p = run(*args())
    out = json.loads(p.stdout)
    assert p.returncode == 0 and set(out) == {"status", "written", "skipped", "errors"} and out["status"] == "ok"
    assert (avault / "intelligence/health/acme/e1.md").is_file()
    p2 = run(*args())
    assert p2.returncode == 0 and json.loads(p2.stdout)["status"] == "skipped" and "skipped (idempotent)" in p2.stderr
    bad = run(*args(entity="Bad"))
    assert bad.returncode == 1 and json.loads(bad.stdout)["errors"][0]["code"] == "INVALID_SLUG"


def test_composes_vault_new_flat_note_no_sidecar(archive, avault):
    archive(*args(entity="e2"))
    assert (avault / "intelligence/health/acme/e2.md").is_file()
    assert not (avault / "intelligence/health/acme/.e2.json").exists()
