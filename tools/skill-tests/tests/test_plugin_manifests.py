import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PLUGIN_DIR = ROOT / "plugins" / "gilberto-core"
PLUGIN_JSON = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = ROOT / ".claude-plugin" / "marketplace.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")


def load(path):
    return json.loads(path.read_text())


def test_plugin_json_fields():
    p = load(PLUGIN_JSON)
    assert p["name"] == "gilberto-core"
    assert SEMVER.match(p["version"])
    assert p["description"].strip()


def test_marketplace_json_fields():
    m = load(MARKETPLACE_JSON)
    assert m["name"].strip()
    assert m["owner"]["name"].strip()
    entries = [e for e in m["plugins"] if e["name"] == "gilberto-core"]
    assert len(entries) == 1
    assert entries[0]["source"] == "./plugins/gilberto-core"


def test_marketplace_name_matches_plugin_and_source_exists():
    entry = next(e for e in load(MARKETPLACE_JSON)["plugins"] if e["name"] == "gilberto-core")
    assert entry["name"] == load(PLUGIN_JSON)["name"]
    assert (ROOT / entry["source"]).is_dir()


def test_plugins_not_pnpm_workspace():
    ws = (ROOT / "pnpm-workspace.yaml").read_text()
    assert "plugins" not in ws


@pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI absent")
@pytest.mark.parametrize("target", [ROOT, PLUGIN_DIR])
def test_claude_plugin_validate(target):
    r = subprocess.run(["claude", "plugin", "validate", str(target)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
