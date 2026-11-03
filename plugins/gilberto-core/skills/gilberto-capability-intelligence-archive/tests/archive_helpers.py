import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"
SKILLS = SCRIPT.parents[1]
sys.path.insert(0, str(SKILLS))

TOPICS = '---\ntype: anatomy-topics\n---\n\n# Topics\n\n| Topic | Description |\n| ----- | ----------- |\n| health | body |\n'
TEMPLATE = '---\ntype: intelligence-note\ntopics: []\n---\n\n# {{title}}\n\nbody\n'
FM = {"type": "intelligence-note"}


def tree(root):
    return {str(p.relative_to(root)): (p.read_bytes() if p.is_file() else None) for p in sorted(root.rglob("*"))}


def args(**over):
    a = {"topic": "health", "source": "acme", "entity": "e1", "template": "note", "frontmatter": json.dumps(FM)}
    a.update(over)
    return [f"--{k}={v}" for k, v in a.items()]
