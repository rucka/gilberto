import json
import signal
import sys


class MechanicError(Exception):
    def __init__(self, code, **extra):
        super().__init__(code)
        self.code = code
        self.extra = extra

    def as_dict(self):
        return {"code": self.code, **self.extra}


def log(msg):
    print(msg, file=sys.stderr)


def emit(status, written=(), skipped=(), errors=()):
    print(json.dumps({"status": status, "written": list(written), "skipped": list(skipped), "errors": list(errors)}))


def run(fn, argv, env):
    """Run fn(argv, env) -> (written, skipped); map MechanicError to JSON + exit 1."""

    def _term(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _term)
    try:
        written, skipped = fn(argv, env)
    except MechanicError as e:
        log(f"error: {e.code}")
        emit("error", errors=[e.as_dict()])
        return 1
    emit("skipped" if skipped and not written else "ok", written, skipped)
    return 0
