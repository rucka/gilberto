import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import anatomy_io, frontmatter, result, validate, vault_io  # noqa: E402
from _lib.atomic_write import Transaction  # noqa: E402
from _lib.result import MechanicError  # noqa: E402
from _lib.url_validate import normalize_url, validate_url  # noqa: E402

TYPES = (
    "rss atom youtube medical oura withings google-calendar outlook-calendar icloud-calendar caldav "
    "gmail outlook-mail imap-mail apple-mail http"
).split()
CADENCES = ("realtime", "hourly", "daily", "weekly", "monthly")
SOURCE_PILLARS = ("pulse", "intelligence", "journey")
_KEY = re.compile(r'^(?:"([^"\n]+)"|(https?://\S+?)):[ \t]*$', re.M)


def _parse(argv):
    p = result.ArgParser(prog="mechanic-forge-source")
    p.add_argument("--type", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--cadence", required=True)
    p.add_argument("--target-pillar", required=True)
    p.add_argument("--target-topic", required=True)
    p.add_argument("--contributor", default="core")
    return p.parse_args(argv)


def _known(text):
    keys = set()
    for m in _KEY.finditer(text):
        try:
            keys.add(normalize_url(m.group(1) or m.group(2)))
        except MechanicError:
            pass
    return keys


def _entry(a):
    return json.dumps(a.url) + f":\n  type: {a.type}\n  cadence: {a.cadence}\n  target_topic: {a.target_topic}\n"


def _run(argv, env):
    a = _parse(argv)
    root = vault_io.vault_root(env)
    validate.slug(a.target_topic)
    validate.slug(a.contributor)
    validate_url(a.url)
    if a.type not in TYPES:
        raise MechanicError("INVALID_TYPE", type=a.type, allowed=list(TYPES))
    if a.cadence not in CADENCES:
        raise MechanicError("INVALID_CADENCE", cadence=a.cadence, allowed=list(CADENCES))
    validate.pillar(root, a.target_pillar)
    if a.target_pillar not in SOURCE_PILLARS:
        raise MechanicError("PILLAR_DOES_NOT_HOLD_SOURCES", pillar=a.target_pillar)
    if not os.path.isdir(vault_io.resolve(root, "anatomy")):
        raise MechanicError("REGISTRY_NOT_FOUND", file="anatomy")

    rel = f"anatomy/playbooks/{a.target_pillar}/sources/{a.contributor}.md"
    folder = vault_io.resolve(root, os.path.dirname(rel))
    path = vault_io.resolve(root, rel)
    block = f"```yaml\n{_entry(a)}```\n"
    today = datetime.date.today().isoformat()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if normalize_url(a.url) in _known(text):
            result.log("skipped (idempotent)")
            return [], [rel]
        sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        new = f"{text}{sep}{block}"
    else:
        fm = {"type": "anatomy-sources", "topics": [], "created": today, "updated": today}
        new = frontmatter.dump(fm, f"\n# Sources — {a.contributor}\n\n{block}")
    try:
        with Transaction() as t:
            t.mkdir(folder)
            t.write(path, new)
    except OSError as e:
        result.log(f"write failed ({e}); rolled back")
        raise MechanicError("WRITE_FAILED", error=str(e), rolledBack=True)
    return [rel], []


def main(argv=None, env=None):
    return result.run(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)


if __name__ == "__main__":
    sys.exit(main())
