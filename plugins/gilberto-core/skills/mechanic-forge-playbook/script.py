import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import frontmatter, result, validate, vault_io  # noqa: E402
from _lib.atomic_write import Transaction  # noqa: E402
from _lib.result import MechanicError  # noqa: E402

DOMAINS = ("ingest", "structure", "surface", "act", "reflect", "next")
MODES = ("core", "contributor")
TRIGGER_KEYS = ("cron", "keyword", "file", "event")
REQUIRED = ("triggers", "dispatch_to", "silence_learned")


def _parse(argv):
    p = result.ArgParser(prog="mechanic-forge-playbook")
    p.add_argument("--event", required=True)
    p.add_argument("--domain", required=True)
    p.add_argument("--mode", required=True)
    p.add_argument("--contributor")
    p.add_argument("--frontmatter", required=True)
    return p.parse_args(argv)


def _frontmatter(raw, event):
    def bad(**extra):
        return MechanicError("INVALID_FRONTMATTER", **extra)

    try:
        fm = json.loads(raw)
    except ValueError:
        fm = None
    if not isinstance(fm, dict):
        raise bad(reason="frontmatter must be a JSON object")
    unknown = sorted(set(fm) - set(REQUIRED) - {"event"})
    missing = [k for k in REQUIRED if k not in fm]
    if unknown or missing:
        raise bad(diff={"missing": missing, "unknown": unknown})
    if fm.get("event", event) != event:
        raise bad(reason="event does not match --event")
    triggers, dispatch, silence = (fm[k] for k in REQUIRED)
    for t in triggers if isinstance(triggers, list) else [None]:
        if not (isinstance(t, dict) and len(t) == 1 and set(t) <= set(TRIGGER_KEYS)
                and all(isinstance(v, str) and v for v in t.values())):
            raise bad(reason=f"triggers must be a list of single-key objects ({'|'.join(TRIGGER_KEYS)}) with string values")
    if not (isinstance(dispatch, list) and all(isinstance(d, str) and validate.SLUG.fullmatch(d) for d in dispatch)):
        raise bad(reason="dispatch_to must be a list of skill names")
    if not (isinstance(silence, list) and all(isinstance(s, dict) for s in silence)):
        raise bad(reason="silence_learned must be a list of objects")
    return {"event": event, "triggers": triggers, "dispatch_to": dispatch, "silence_learned": silence}


def _run(argv, env):
    a = _parse(argv)
    root = vault_io.vault_root(env)
    validate.slug(a.event)
    if a.domain not in DOMAINS:
        raise MechanicError("INVALID_DOMAIN", domain=a.domain)
    if a.mode not in MODES:
        raise MechanicError("INVALID_MODE", mode=a.mode)
    if (a.mode == "contributor") != (a.contributor is not None):
        raise MechanicError("INVALID_ARGS", detail="--contributor is required in contributor mode and only allowed there")
    if a.contributor is not None:
        validate.slug(a.contributor)
    fm = _frontmatter(a.frontmatter, a.event)
    if not os.path.isdir(vault_io.resolve(root, "anatomy")):
        raise MechanicError("REGISTRY_NOT_FOUND", file="anatomy")

    base = f"anatomy/playbooks/{a.domain}"
    rel = f"{base}/{a.event}/{a.contributor}.md" if a.contributor else f"{base}/{a.event}.md"
    path = vault_io.resolve(root, rel)
    if os.path.exists(path):
        result.log("skipped (idempotent)")
        return [], [rel]
    title = a.event.replace("-", " ").title()
    try:
        with Transaction() as t:
            t.mkdir(os.path.dirname(path))
            t.write(path, frontmatter.dump(fm, f"\n# {title}\n\nPlaceholder: describe the playbook steps.\n"))
    except OSError as e:
        result.log(f"write failed ({e}); rolled back")
        raise MechanicError("WRITE_FAILED", error=str(e), rolledBack=True)
    return [rel], []


def main(argv=None, env=None):
    return result.run(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)


if __name__ == "__main__":
    sys.exit(main())
