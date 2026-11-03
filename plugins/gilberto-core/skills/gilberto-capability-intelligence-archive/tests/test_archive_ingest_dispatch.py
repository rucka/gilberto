import json
import os
import subprocess
import sys

import pytest
from archive_helpers import SKILLS

INGEST = SKILLS / "gilberto-process-ingest" / "script.py"
PLUGINS = SKILLS.parents[1]
PDF = b"%PDF-1.4\x00\xff\xfe binary"
NOTE = b"# note\nbody \xc3\xa9\n"


@pytest.fixture
def ingest(avault):
    (avault / "_ingest").mkdir(exist_ok=True)
    env = {**os.environ, "GILBERTO_ROOT": str(avault), "GILBERTO_SKILLS_DIR": str(PLUGINS)}

    def cli(*argv):
        p = subprocess.run([sys.executable, str(INGEST), *argv], capture_output=True, text=True, env=env, timeout=60)
        return p, json.loads(p.stdout)

    def put(name, body, sub=""):
        d = avault / "_ingest" / sub
        d.mkdir(exist_ok=True)
        (d / os.path.basename(name)).write_bytes(body)
        os.utime(d / os.path.basename(name), (1, 1))

    def apply(name, body=NOTE, confidence="0.99", sub=""):
        put(name, body, sub)
        return cli("apply", f"--file={sub + '/' if sub else ''}{name}", "--pillar=intelligence", f"--confidence={confidence}", "--min-age=0")

    return type("I", (), {"cli": staticmethod(cli), "apply": staticmethod(apply)})


def sidecar(avault, rel, source):
    side = json.loads((avault / (rel + ".ingest.json")).read_text())
    assert side["source"] == source and side["pillar"] == "intelligence" and side["confidence"] == 0.99
    assert side["ingested_at"]


def test_ingest_dispatch_archives_intelligence_e2e(ingest, avault):
    p, out = ingest.apply("a.md")
    assert out["status"] == "archived", (out, p.stderr)
    assert out["archived"] == "intelligence/a.md"
    assert (avault / "intelligence/a.md").read_bytes() == NOTE
    sidecar(avault, "intelligence/a.md", "_ingest/a.md")
    assert not (avault / "_ingest/a.md.error.md").exists() and not (avault / "_ingest/a.md").exists()


def test_ingest_dispatch_name_collision_e2e(ingest, avault):
    (avault / "intelligence/a.md").write_text("existing\n")
    before = (avault / "intelligence/a.md").read_text()
    p, out = ingest.apply("a.md")
    assert out["status"] == "archived", (out, p.stderr)
    assert out["archived"] == "intelligence/a-1.md" and (avault / out["archived"]).read_bytes() == NOTE
    assert (avault / "intelligence/a.md").read_text() == before
    assert not (avault / "_ingest/a.md.error.md").exists()


def test_ingest_dispatch_orphan_sidecar_collision_e2e(ingest, avault):
    (avault / "intelligence/a.md.ingest.json").write_text("orphan\n")
    p, out = ingest.apply("a.md")
    assert out["status"] == "archived", (out, p.stderr)
    assert out["archived"] != "intelligence/a.md" and (avault / out["archived"]).read_bytes() == NOTE
    assert not (avault / "intelligence/a.md").exists()
    assert (avault / "intelligence/a.md.ingest.json").read_text() == "orphan\n"


@pytest.mark.parametrize("name", ["a.pdf", "a.png"])
def test_ingest_dispatch_binary_source_byte_identical_e2e(ingest, avault, name):
    p, out = ingest.apply(name, PDF)
    assert out["status"] == "archived", (out, p.stderr)
    assert out["archived"] == f"intelligence/{name}" and (avault / out["archived"]).read_bytes() == PDF
    sidecar(avault, out["archived"], f"_ingest/{name}")
    assert not (avault / f"_ingest/{name}.error.md").exists()


def test_ingest_confirm_archives_below_threshold_e2e(ingest, avault):
    p, kept = ingest.apply("a.md", confidence="0.01")
    assert kept["status"] == "kept", (kept, p.stderr)
    assert (avault / "_ingest/a.md.classification.json").is_file()
    p, out = ingest.cli("confirm", "--file=a.md")
    assert out["status"] == "archived", (out, p.stderr)
    assert out["archived"] == "intelligence/a.md" and (avault / "intelligence/a.md").read_bytes() == NOTE
    assert json.loads((avault / "intelligence/a.md.ingest.json").read_text())["confidence"] == 1.0
    left = sorted(x.name for x in (avault / "_ingest").iterdir() if not x.name.startswith("."))
    assert left == []


def test_ingest_dispatch_subdir_source_e2e(ingest, avault):
    p, out = ingest.apply("a.md", sub="intelligence")
    assert out["status"] == "archived", (out, p.stderr)
    assert out["archived"] == "intelligence/a.md" and (avault / "intelligence/a.md").read_bytes() == NOTE
    sidecar(avault, "intelligence/a.md", "_ingest/intelligence/a.md")
    assert not (avault / "_ingest/intelligence/a.md").exists()
    assert not (avault / "_ingest/intelligence/a.md.error.md").exists()


NON_SLUG = ["Q3 Report.pdf", "Report.PDF", "notes.v2.md", "Résumé Été.md", "x" * 70 + ".md", "UPPER.MD"]


@pytest.mark.parametrize("name", NON_SLUG)
def test_ingest_dispatch_non_slug_basename_e2e(ingest, avault, name):
    p, out = ingest.apply(name, PDF)
    assert out["status"] == "archived", (out, p.stderr)
    assert out["archived"] == f"intelligence/{name}" and (avault / out["archived"]).read_bytes() == PDF
    sidecar(avault, out["archived"], f"_ingest/{name}")
    assert not (avault / f"_ingest/{name}.error.md").exists() and not (avault / f"_ingest/{name}").exists()


@pytest.mark.parametrize("name", ["a.txt", "a.html", "a.docx", "a.jpg", "a.jpeg"])
def test_ingest_dispatch_remaining_extensions_byte_identical_e2e(ingest, avault, name):
    p, out = ingest.apply(name, PDF)
    assert out["status"] == "archived", (out, p.stderr)
    assert out["archived"] == f"intelligence/{name}" and (avault / out["archived"]).read_bytes() == PDF
    sidecar(avault, out["archived"], f"_ingest/{name}")
    assert not (avault / f"_ingest/{name}.error.md").exists()
