"""Compose the adopted shared rules and one approved host adapter."""

import argparse
from pathlib import Path
import re
import sys


def compose(common: str, adapters: str, host: str) -> str:
    sections = re.split(r"(?m)^<!-- host:([a-z][a-z0-9-]*) -->[ \t]*\r?$", adapters)
    by_host = {}
    for name, body in zip(sections[1::2], sections[2::2]):
        if name in by_host:
            raise ValueError(f"Duplicate host adapter: {name}")
        by_host[name] = body.strip()
    if not common.strip():
        raise ValueError("The shared host rules are empty.")
    if not by_host.get(host):
        raise ValueError(f"No adapter defined for {host}.")
    return common.rstrip() + "\n\n" + by_host[host] + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--common", type=Path, required=True)
    parser.add_argument("--adapters", type=Path, required=True)
    parser.add_argument("--host", required=True)
    args = parser.parse_args()
    try:
        rendered = compose(
            args.common.read_text(encoding="utf-8-sig"),
            args.adapters.read_text(encoding="utf-8-sig"),
            args.host,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    sys.stdout.buffer.write(rendered.encode("utf-8"))


if __name__ == "__main__":
    main()
