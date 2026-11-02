def block(url, **fields):
    body = "".join(f"  {k}: {v}\n" for k, v in fields.items())
    return f'```yaml\n"{url}":\n{body}```\n'
