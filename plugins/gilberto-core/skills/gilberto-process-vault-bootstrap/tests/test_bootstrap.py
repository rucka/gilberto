import importlib.util
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bootstrap", HERE / "script.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PILLARS = "".join(f'wrote dir="{d}"\n' for d in ["me", "pulse", "projects", "intelligence", "journey", "network"])
SEEDS = "".join(f'wrote file="anatomy/{f}.md"\n' for f in "anatomy gilberto topics plugins preferences a b c".split())
TRACE = f'{PILLARS}wrote dir="network/people"\nstep=skeleton decision=written target="/v"\n{SEEDS}merged-keys=a,b\nstep=launchd decision=skipped\n'
STDOUT = "plugins: none\n"

@pytest.fixture
def fake(monkeypatch):
    """fake(which=, npm=, version=, spawn=(code,out,err)) -> list of spawned argvs"""

    def setup(which=None, npm_version=None, version="0.1.0", result=(0, STDOUT, TRACE)):
        spawned = []
        monkeypatch.setattr(mod.shutil, "which", lambda n, path=None: which)

        def run(argv, **kw):
            s = lambda out="", code=0: SimpleNamespace(stdout=out, stderr="", returncode=code)
            if argv[-1] == "--version":
                return s(version)
            if argv[:3] == ["npm", "ls", "-g"]:
                return s(json.dumps({"dependencies": {"gilberto": {"version": npm_version}}} if npm_version else {}))
            if argv[:3] == ["npm", "prefix", "-g"]:
                return s("/np\n")
            spawned.append(argv)
            return s()

        monkeypatch.setattr(mod, "run", run)
        monkeypatch.setattr(mod, "spawn", lambda argv, env: (spawned.append(argv), result)[1])
        return spawned

    return setup


def test_ac1_no_cli_uses_npx(fake, capsys):
    sp = fake()
    assert mod.main(["--target-path=/v"], {}, "darwin") == 0
    assert sp[0][:3] == ["npx", "-y", "gilberto@latest"] and sp[0][3:5] == ["install", "/v"] and "--non-interactive" in sp[0]


def test_ac2_global_cli_direct(fake):
    sp = fake(which="/usr/bin/gilberto")
    assert mod.main(["--target-path=/v"], {}, "darwin") == 0
    assert sp[0][0] == "/usr/bin/gilberto" and "npx" not in sp[0]


def test_npm_global_fallback(fake):
    sp = fake(npm_version="1.2.3")
    mod.main([], {}, "darwin")
    assert sp[0][0] == "/np/bin/gilberto"


def test_ac3_version_below_range(fake, capsys):
    sp = fake(which="/g", version="0.0.9")
    assert mod.main([], {}, "darwin") == 64 and not sp
    assert "installed gilberto version 0.0.9 is below required >=0.1.0 <2; upgrade with `npm i -g gilberto@latest` or rerun via `npx gilberto@latest`" in capsys.readouterr().err
    sp = fake(which="/g", version="0.0.9")
    mod.main(["--confirm=npx"], {}, "darwin")
    assert sp[0][0] == "npx"


def test_version_above_range(fake):
    sp = fake(which="/g", version="2.0.0")
    assert mod.main([], {}, "darwin") == 64


def test_ac4_args_to_flags(fake):
    sp = fake(which="/g")
    mod.main(["--target-path=/a b", "--seed-topics=pulse=x", "--disable-hooks", "--disable-launchd"], {}, "darwin")
    assert sp[0] == ["/g", "install", "/a b", "--non-interactive", "-v", "--seed-topics=pulse=x", "--no-hooks", "--no-launchd"]


def test_ac4_defaults(fake):
    sp = fake(which="/g")
    mod.main([], {}, "darwin")
    assert sp[0] == ["/g", "install", "--non-interactive", "-v"]


def test_ac5_registry_unreachable(fake, capsys):
    fake(result=(1, "", "npm error code ENOTFOUND"))
    assert mod.main([], {}, "darwin") == 1
    assert "npm registry unreachable; install gilberto manually via the steps at" in capsys.readouterr().err


def test_ac6_summary(fake, capsys):
    fake(which="/g")
    assert mod.main([], {}, "darwin") == 0
    o = capsys.readouterr().out
    assert "vault: /v" in o and "pillars: 6" in o and "anatomy seeds: 8" in o and "hooks: merged" in o and "launchd: skipped" in o
    assert "wrote dir" not in o
    mod.main(["--verbose"], {}, "darwin")
    assert "wrote dir" in capsys.readouterr().out


def test_ac7_exit2_verbatim(fake, capsys):
    sp = fake(which="/g", result=(2, "", "vault exists; use upgrade\n"))
    assert mod.main([], {}, "darwin") == 2
    assert capsys.readouterr().err == "vault exists; use upgrade\n" and len(sp) == 1


@pytest.mark.parametrize("code", [1, 13, 28, 64, 65, 70, 130])
def test_known_exit_codes(fake, capsys, code):
    fake(which="/g", result=(code, "", "boom"))
    assert mod.main([], {}, "darwin") == code
    err = capsys.readouterr().err
    assert f"(exit {code})" in err and "boom" in err


def test_unknown_exit(fake, capsys):
    fake(which="/g", result=(7, "", "x"))
    assert mod.main([], {}, "darwin") == 7
    assert "unexpected CLI failure (exit 7)" in capsys.readouterr().err


def test_ac8_linux_injects(fake, capsys):
    sp = fake(which="/g")
    mod.main([], {}, "linux")
    assert "--no-launchd" in sp[0]
    assert "auto-injected --no-launchd" in capsys.readouterr().out


def test_ac8_explicit_no_note(fake, capsys):
    sp = fake(which="/g")
    mod.main(["--disable-launchd"], {}, "linux")
    assert sp[0].count("--no-launchd") == 1 and "auto-injected" not in capsys.readouterr().out


def test_ac10_local_bin_ignored(tmp_path, monkeypatch):
    local = tmp_path / "proj" / "node_modules" / ".bin"
    local.mkdir(parents=True)
    exe = local / "gilberto"
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)
    env = {"PATH": f"{local}:/nonexistent"}
    monkeypatch.setenv("PATH", env["PATH"])
    monkeypatch.setattr(mod, "run", lambda argv, **kw: SimpleNamespace(stdout="{}", stderr="", returncode=0))
    cli = mod.detect(env)
    assert cli["source"] == "npx" and cli["argv"] == ["npx", "-y", "gilberto@latest"]


def test_no_fs_mutation(fake, tmp_path, monkeypatch):
    sp = fake(which="/g")
    monkeypatch.chdir(tmp_path)
    before = sorted(tmp_path.rglob("*"))
    mod.main(["--target-path=/v"], {}, "darwin")
    assert sorted(tmp_path.rglob("*")) == before


def test_skill_frontmatter_and_manifest():
    fm = (HERE / "SKILL.md").read_text().split("---")[1]
    kv = dict(l.split(": ", 1) for l in fm.strip().splitlines())
    assert kv["name"] == HERE.name and re.fullmatch(r"gilberto-process-[a-z]+-[a-z]+", kv["name"])
    assert kv["description"] and kv["requires"] == "gilberto@>=0.1.0 <2"
    manifest = json.loads((HERE.parent.parent / ".claude-plugin" / "plugin.json").read_text())
    assert f"./skills/{kv['name']}" in manifest["skills"]
