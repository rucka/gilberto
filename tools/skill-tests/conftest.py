import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent


@pytest.fixture
def synthetic_vault(tmp_path):
    """Tmp-dir vault skeleton.

    Layout: inbox/, notes/, projects/, journal/ (empty dirs) + README.md.
    """
    vault = tmp_path / "vault"
    for d in ("inbox", "notes", "projects", "journal"):
        (vault / d).mkdir(parents=True)
    (vault / "README.md").write_text("# Synthetic vault\n")
    return vault


@pytest.fixture
def run_harness():
    """Copy harness config to root/tools/skill-tests, lay out root/plugins/<p>/skills/<s>/<files>, run pytest."""

    def run(root, skills):
        h = root / "tools" / "skill-tests"
        h.mkdir(parents=True)
        for f in ("pyproject.toml", "conftest.py"):
            shutil.copy(HARNESS / f, h / f)
        for plugin, skill, files in skills:
            d = root / "plugins" / plugin / "skills" / skill
            for rel, body in files.items():
                (d / rel).parent.mkdir(parents=True, exist_ok=True)
                (d / rel).write_text(body)
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"], cwd=h, capture_output=True, text=True
        )

    return run
