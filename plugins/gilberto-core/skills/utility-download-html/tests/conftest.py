import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dl_helpers import SCRIPT, Resp


@pytest.fixture
def mod():
    spec = importlib.util.spec_from_file_location("utility_download_html", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m._resolve = lambda host: ["93.184.216.34"]
    m._open = lambda req, timeout: Resp()
    return m


@pytest.fixture
def root(tmp_path):
    (tmp_path / "_ingest").mkdir()
    return tmp_path


@pytest.fixture
def run(mod, root, capsys):
    def go(*argv, env_root=None):
        capsys.readouterr()
        code = mod.main(list(argv), {"GILBERTO_ROOT": str(env_root or root)})
        out = capsys.readouterr()
        return code, json.loads(out.out), out.err

    return go
