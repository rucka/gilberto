import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rss_helpers import SCRIPT, Resp, fixture

@pytest.fixture
def mod():
    spec = importlib.util.spec_from_file_location("utility_fetch_rss", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m._sleep = lambda s: None
    m._open = lambda req, timeout: Resp(fixture("feed.xml"))
    return m


@pytest.fixture
def root(tmp_path):
    return tmp_path


@pytest.fixture
def serve(mod):
    def go(*responses):
        queue = list(responses)
        calls = []

        def _open(req, timeout):
            calls.append(req.full_url)
            r = queue.pop(0) if len(queue) > 1 else queue[0]
            if isinstance(r, Exception):
                raise r
            return r

        mod._open = _open
        return calls

    return go


@pytest.fixture
def run(mod, root, capsys):
    def go(*argv, env_root=None):
        capsys.readouterr()
        code = mod.main(list(argv), {"GILBERTO_ROOT": str(env_root or root)})
        out = capsys.readouterr()
        return code, json.loads(out.out), out.err

    return go
