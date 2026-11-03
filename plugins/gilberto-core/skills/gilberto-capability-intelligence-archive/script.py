import datetime
import importlib.util
import json
import os
import sys

SKILLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, SKILLS)

from _lib import anatomy_io, frontmatter, result, validate, vault_io  # noqa: E402
from _lib.result import MechanicError  # noqa: E402

PILLAR = "intelligence"
UNCATEGORIZED = "_uncategorized"
VOLATILE = ("created", "updated")


def _vault_new():
    spec = importlib.util.spec_from_file_location("mechanic_vault_new", os.path.join(SKILLS, "mechanic-vault-new", "script.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse(argv):
    p = result.ArgParser(prog="gilberto-capability-intelligence-archive")
    for k in ("topic", "source", "entity", "template"):
        p.add_argument(f"--{k}", required=True)
    p.add_argument("--frontmatter", default="{}")
    p.add_argument("--confirm-topic", action="store_true")
    p.add_argument("--confirm-source", action="store_true")
    return p.parse_args(argv)


def _known_topic(root, topic):
    try:
        return anatomy_io.has_topic(anatomy_io.read(root, anatomy_io.TOPICS), topic)
    except MechanicError:
        return False


def _known_source(root, topic, source):
    return os.path.isfile(os.path.join(root, f"anatomy/playbooks/{PILLAR}/sources/{source}.md")) or os.path.isdir(
        os.path.join(root, PILLAR, topic, source)
    )


def _run(argv, env):
    a = _parse(argv)
    root = vault_io.vault_root(env)
    for v in (a.topic, a.source, a.entity, a.template):
        validate.slug(v)
    vn = _vault_new()
    supplied = vn._supplied(a.frontmatter)

    topic = a.topic
    if not (a.confirm_topic or _known_topic(root, topic)):
        topic = UNCATEGORIZED
        result.log(f"unknown topic {a.topic!r}; placing under {PILLAR}/{UNCATEGORIZED}/")
    if not _known_source(root, topic, a.source) and not a.confirm_source:
        raise MechanicError("SOURCE_UNCONFIRMED", source=a.source)
    supplied = {"topics": [] if topic == UNCATEGORIZED else [topic], **supplied}

    rel = f"{PILLAR}/{topic}/{a.source}/{a.entity}.md"
    note = vault_io.resolve(root, rel)
    if os.path.exists(note):
        want_fm, want_body = vn.render(root, PILLAR, a.template, supplied, "")
        with open(note, encoding="utf-8") as f:
            have_fm, have_body = frontmatter.parse(f.read())
        strip = lambda fm: {k: v for k, v in fm.items() if k not in VOLATILE}
        if strip(have_fm) != strip(want_fm) or have_body != want_body:
            raise MechanicError("CONFLICT", path=rel)
        result.log("skipped (idempotent)")
        return [], [rel]
    return vn._run(
        [f"--pillar={PILLAR}", f"--template={a.template}", f"--slug={a.entity}", f"--path={topic}/{a.source}", f"--frontmatter={json.dumps(supplied)}"],
        env,
    )


def main(argv=None, env=None):
    return result.run(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)


if __name__ == "__main__":
    sys.exit(main())
