import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "script.py"
URL = "https://feeds.example.com/rss"


class Resp:
    def __init__(self, data, status=200):
        self.data, self.status = data, status

    def read(self, n=-1):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fixture(name):
    return (HERE / "fixtures" / name).read_bytes()


def http_error(code):
    return urllib.error.HTTPError(URL, code, "x", {}, None)
