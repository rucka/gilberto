from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "script.py"


def block(url, **fields):
    body = "".join(f"  {k}: {v}\n" for k, v in fields.items())
    return f'```yaml\n"{url}":\n{body}```\n'
