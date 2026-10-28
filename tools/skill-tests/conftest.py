import pytest


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
