import sys
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "script.py"
sys.path.insert(0, str(HERE.parents[1]))
ARTICLE = (HERE / "fixtures" / "article.html").read_bytes()
URL = "https://blog.example.com/posts/slow-mornings"
CHROME = ["NAVHOME", "NAVABOUT", "ADSPONSORED", "SIDEBARRELATED", "FOOTERCOPYRIGHT", "FOOTERPRIVACY"]


class Resp:
    def __init__(self, body=ARTICLE, status=200, ctype="text/html; charset=utf-8"):
        self.status, self.body, self.headers = status, body, {"Content-Type": ctype}

    def read(self, n=-1):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def err_code(out):
    return out["errors"][0]["code"]
