import os


def atomic_write(path, data):
    tmp = f"{path}.tmp.{os.getpid()}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


class Transaction:
    """Tracks created files/dirs; removes them if the block raises (incl. KeyboardInterrupt)."""

    def __init__(self):
        self.files = []
        self.dirs = []

    def __enter__(self):
        return self

    def mkdir(self, path):
        missing = []
        p = path
        while not os.path.isdir(p):
            missing.append(p)
            p = os.path.dirname(p)
        for d in reversed(missing):
            os.mkdir(d)
            self.dirs.append(d)

    def write(self, path, data):
        existed = os.path.exists(path)
        atomic_write(path, data)
        if not existed:
            self.files.append(path)

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            return False
        for f in reversed(self.files):
            try:
                os.unlink(f)
            except OSError:
                pass
        for d in reversed(self.dirs):
            try:
                os.rmdir(d)
            except OSError:
                pass
        return False
