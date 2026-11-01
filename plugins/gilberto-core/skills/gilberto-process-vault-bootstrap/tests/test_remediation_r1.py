import importlib.util
import os
import stat
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bootstrap_r1", HERE / "script.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PILLARS = "".join(f'wrote dir="{d}"\n' for d in ["me", "pulse", "projects", "intelligence", "journey", "network"])
SEEDS = "".join(f'wrote file="anatomy/{f}.md"\n' for f in "anatomy gilberto topics plugins preferences a b c".split())
TRACE = f'{PILLARS}step=skeleton decision=written target="/v"\n{SEEDS}merged-keys=a,b\nstep=launchd decision=skipped\n'


def stub(path, body):
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def cli_stub(d, version="0.1.0", code=0, err=TRACE, out="plugins: none\n"):
    (d / "ver").write_text(version)
    (d / "err").write_text(err)
    (d / "out").write_text(out)
    stub(
        d / "gilberto",
        f'D="$(dirname "$0")"\n'
        'echo "$@" >> "$D/calls"\n'
        'if [ "$1" = "--version" ]; then cat "$D/ver"; exit 0; fi\n'
        'cat "$D/out"; cat "$D/err" >&2\n'
        f"exit {code}\n",
    )


def npm_stub(d, new_version=None, code=0):
    bump = f'echo {new_version} > "$D/ver"\n' if new_version else ""
    stub(d / "npm", f'D="$(dirname "$0")"\necho "npm $@" >> "$D/calls"\n{bump}exit {code}\n')


def npx_stub(d, code, err, out=""):
    (d / "npx_err").write_text(err)
    (d / "npx_out").write_text(out)
    stub(d / "npx", f'D="$(dirname "$0")"\ncat "$D/npx_out"; cat "$D/npx_err" >&2\nexit {code}\n')


def calls(d):
    f = d / "calls"
    return f.read_text().splitlines() if f.exists() else []


def env_for(*dirs):
    return {"PATH": os.pathsep.join([*map(str, dirs), "/usr/bin", "/bin"])}


def test_r0_2_summary_parses_stderr_trace(tmp_path, capsys):
    cli_stub(tmp_path)
    assert mod.main(["--target-path=/v", "--disable-launchd"], env_for(tmp_path), "darwin") == 0
    o = capsys.readouterr().out
    for want in ["vault: /v", "pillars: 6", "anatomy seeds: 8", "hooks: merged", "launchd: skipped"]:
        assert want in o
    assert "wrote dir" not in o


def test_r0_2_verbose_appends_trace(tmp_path, capsys):
    cli_stub(tmp_path)
    assert mod.main(["--verbose"], env_for(tmp_path), "darwin") == 0
    o = capsys.readouterr().out
    assert 'wrote dir="me"' in o and "merged-keys=a,b" in o


def test_r0_2_hooks_skipped_without_merged_keys(tmp_path, capsys):
    cli_stub(tmp_path, err=TRACE.replace("merged-keys=a,b\n", ""))
    assert mod.main([], env_for(tmp_path), "darwin") == 0
    assert "hooks: skipped" in capsys.readouterr().out


def test_r0_3_trace_network_dir_not_registry_error(tmp_path, capsys):
    npx_stub(tmp_path, 65, 'wrote dir="network"\nexisting .claude/settings.json is not valid JSON\n')
    assert mod.main([], env_for(tmp_path), "darwin") == 65
    err = capsys.readouterr().err
    assert "(exit 65)" in err and "registry unreachable" not in err


def test_r0_3_real_registry_error_still_unreachable(tmp_path, capsys):
    npx_stub(tmp_path, 1, "npm error code ENOTFOUND\nnpm error network request failed\n")
    assert mod.main([], env_for(tmp_path), "darwin") == 1
    assert "npm registry unreachable" in capsys.readouterr().err


def test_r0_3_registry_error_after_trace_still_unreachable_boundary(tmp_path, capsys):
    npx_stub(tmp_path, 1, "npm error code ECONNREFUSED\n")
    assert mod.main([], env_for(tmp_path), "darwin") == 1
    assert "npm registry unreachable" in capsys.readouterr().err


@pytest.mark.parametrize("sig", ["ETIMEDOUT", "EAI_AGAIN", "ECONNRESET", "network"])
def test_r0_3_each_signature_unreachable(tmp_path, capsys, sig):
    npx_stub(tmp_path, 1, f"npm error {sig}\n")
    assert mod.main([], env_for(tmp_path), "darwin") == 1
    assert "npm registry unreachable" in capsys.readouterr().err


def test_r0_6_upgrade_still_out_of_range_exits_64(tmp_path, capsys):
    cli_stub(tmp_path, version="0.0.9")
    npm_stub(tmp_path)
    assert mod.main(["--confirm=upgrade"], env_for(tmp_path), "darwin") == 64
    assert "0.0.9" in capsys.readouterr().err
    assert not any(c.startswith("install") for c in calls(tmp_path))


def test_r0_6_upgrade_to_above_range_says_outside(tmp_path, capsys):
    cli_stub(tmp_path, version="0.0.9")
    npm_stub(tmp_path, new_version="2.0.0")
    assert mod.main(["--confirm=upgrade"], env_for(tmp_path), "darwin") == 64
    err = capsys.readouterr().err
    assert "outside" in err and "2.0.0" in err and "below" not in err
    assert not any(c.startswith("install") for c in calls(tmp_path))


def test_r0_6_upgrade_in_range_runs_install(tmp_path):
    cli_stub(tmp_path, version="0.0.9")
    npm_stub(tmp_path, new_version="0.2.0")
    assert mod.main(["--confirm=upgrade"], env_for(tmp_path), "darwin") == 0
    assert any(c.startswith("install") for c in calls(tmp_path))


def test_r0_6_upgrade_npm_failure_relayed(tmp_path):
    cli_stub(tmp_path, version="0.0.9")
    npm_stub(tmp_path, code=3)
    assert mod.main(["--confirm=upgrade"], env_for(tmp_path), "darwin") == 3
    assert not any(c.startswith("install") for c in calls(tmp_path))


def test_r0_6_version_above_range_says_outside(tmp_path, capsys):
    cli_stub(tmp_path, version="2.0.0")
    assert mod.main([], env_for(tmp_path), "darwin") == 64
    err = capsys.readouterr().err
    assert "outside" in err and "below" not in err


@pytest.fixture
def local_bin(tmp_path):
    local = tmp_path / "proj" / "node_modules" / ".bin"
    local.mkdir(parents=True)
    cli_stub(local)
    npx = tmp_path / "npxdir"
    npx.mkdir()
    npx_stub(npx, 0, TRACE)
    return local, npx


def test_r0_7_verbose_announces_ignored_local(local_bin, capsys):
    local, npx = local_bin
    mod.main(["--verbose"], env_for(local, npx), "darwin")
    c = capsys.readouterr()
    assert "ignored local gilberto at" in c.out + c.err and str(local) in c.out + c.err
    assert not calls(local)


def test_r0_7_not_verbose_stays_silent(local_bin, capsys):
    local, npx = local_bin
    mod.main([], env_for(local, npx), "darwin")
    c = capsys.readouterr()
    assert "ignored local" not in c.out + c.err


def test_r0_7_verbose_without_local_gilberto_silent(tmp_path, capsys):
    empty = tmp_path / "proj" / "node_modules" / ".bin"
    empty.mkdir(parents=True)
    npx = tmp_path / "npxdir"
    npx.mkdir()
    npx_stub(npx, 0, TRACE)
    mod.main(["--verbose"], env_for(empty, npx), "darwin")
    c = capsys.readouterr()
    assert "ignored local" not in c.out + c.err


def test_r0_7_verbose_announces_ignored_local_with_global_present(local_bin, tmp_path, capsys):
    local, npx = local_bin
    glob = tmp_path / "globalbin"
    glob.mkdir()
    cli_stub(glob)
    assert mod.main(["--verbose"], env_for(local, glob, npx), "darwin") == 0
    c = capsys.readouterr()
    assert "ignored local gilberto at" in c.out + c.err and str(local) in c.out + c.err
    assert any(x.startswith("install") for x in calls(glob))
    assert not calls(local)
