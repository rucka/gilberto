import json
import os
import subprocess
import sys

from fetch_helpers import SCRIPT, block

A = {"id": "a", "markdown": "---\ntype: article\n---\n\nA\n"}


def cli(root, utility, *argv):
    p = subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        env={**os.environ, "GILBERTO_ROOT": str(root), "GILBERTO_UTILITY_PATH": utility.path},
        capture_output=True,
        text=True,
    )
    return p.returncode, json.loads(p.stdout)


def test_all_acs_via_cli(fetch, source, utility):
    source(
        "intelligence",
        "core",
        block("https://feed.example/rss", type="rss"),
        block("https://mail.example/inbox", type="gmail", provider="gmail", profile="learnn"),
        block("https://chat.example/c", type="slack", provider="slack", fallback="mcp"),
        block("https://x.example/n", type="nope"),
    )
    source("pulse", "core", block("https://p.example/f", type="rss"))
    utility("utility-fetch-rss", [A])
    utility("utility-gmail-read", [{"id": "m", "markdown": "M"}])
    # AC-1/2/3/5: load all, dispatch by provider/type, profile passed, mcp fallback, unknown type isolated
    code, out = cli(fetch.root, utility)
    assert code == 1 and out["status"] == "partial"
    assert len(out["written"]) == 3
    assert utility.args("utility-gmail-read") == ["--url=https://mail.example/inbox", "--profile=learnn"]
    assert [e["code"] for e in out["errors"]] == ["UNKNOWN_TYPE"]
    assert [s["reason"] for s in out["skipped"]] == ["mcp-fallback"]
    # AC-4: re-run skips fetched items
    code, again = cli(fetch.root, utility)
    assert again["written"] == [] and sorted(s["reason"] for s in again["skipped"]) == ["already-fetched"] * 3 + ["mcp-fallback"]
    # AC-6: filters
    _, only = cli(fetch.root, utility, "--pillar=pulse")
    assert only["written"] == [] and len(only["skipped"]) == 1
    _, only = cli(fetch.root, utility, "--source=https://feed.example/rss")
    assert len(only["skipped"]) == 1
