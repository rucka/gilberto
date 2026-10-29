import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _lib import anatomy_io, frontmatter, result, validate, vault_io  # noqa: E402
from _lib.atomic_write import Transaction  # noqa: E402
from _lib.result import MechanicError  # noqa: E402

RESERVED = validate.PILLARS + ("anatomy",)


def _parse(argv):
    p = result.ArgParser(prog="mechanic-forge-topic")
    p.add_argument("--slug", required=True)
    p.add_argument("--seed", default="")
    p.add_argument("--description", default="")
    return p.parse_args(argv)


def _note(root, pillar, slug, today):
    title = slug.replace("-", " ").title()
    tpl = vault_io.resolve(root, f"anatomy/templates/{pillar}/topic/topic.md")
    if os.path.isfile(tpl):
        with open(tpl, encoding="utf-8") as f:
            return anatomy_io.render(f.read(), slug, title, today)
    fm = {"type": f"{pillar}-topic", "topics": [slug], "created": today, "updated": today}
    return frontmatter.dump(fm, f"\n# {title}\n")


def _run(argv, env):
    a = _parse(argv)
    root = vault_io.vault_root(env)
    validate.slug(a.slug)
    if a.slug in RESERVED:
        raise MechanicError("RESERVED_NAME", input=a.slug)
    seeds = list(dict.fromkeys(s for s in a.seed.split(",") if s))
    for s in seeds:
        if s not in validate.PILLARS:
            raise MechanicError("INVALID_SEED_PILLAR", pillar=s)
    for s in seeds:
        validate.pillar(root, s)
    topics = vault_io.resolve(root, anatomy_io.TOPICS)
    text = anatomy_io.read(root, anatomy_io.TOPICS)
    today = datetime.date.today().isoformat()

    written, skipped = [], []
    try:
        with Transaction() as t:
            for p in seeds:
                rel = f"{p}/{a.slug}"
                folder = vault_io.resolve(root, rel)
                note = os.path.join(folder, f"{a.slug}.md")
                if not os.path.isdir(folder):
                    t.mkdir(folder)
                    written.append(rel)
                if os.path.exists(note):
                    skipped.append(f"{rel}/{a.slug}.md")
                else:
                    t.write(note, _note(root, p, a.slug, today))
                    written.append(f"{rel}/{a.slug}.md")
                history = os.path.join(folder, "history")
                if p == "pulse" and not os.path.isdir(history):
                    t.mkdir(history)
                    written.append(f"{rel}/history")
            if anatomy_io.has_topic(text, a.slug):
                skipped.append(anatomy_io.TOPICS)
            else:
                t.write(topics, anatomy_io.append_topic(text, a.slug, a.description))
                written.append(anatomy_io.TOPICS)
    except OSError as e:
        result.log(f"write failed ({e}); rolled back")
        raise MechanicError("WRITE_FAILED", error=str(e), rolledBack=True)
    if not written:
        result.log("skipped (idempotent)")
    return written, skipped


def main(argv=None, env=None):
    return result.run(_run, sys.argv[1:] if argv is None else argv, os.environ if env is None else env)


if __name__ == "__main__":
    sys.exit(main())
