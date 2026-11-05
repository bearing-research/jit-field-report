"""Download the pipeline inputs listed in data/MANIFEST.toml and verify checksums.

  python scripts/fetch_data.py            # downloads into data/
  python scripts/fetch_data.py --check    # verify existing files only
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    manifest = tomllib.loads((DATA / "MANIFEST.toml").read_text())
    ok = True
    for name, entry in manifest["files"].items():
        path = DATA / entry["file"]
        if not path.exists() and not args.check:
            print(f"downloading {name} from {entry['url']}")
            urllib.request.urlretrieve(entry["url"], path)
        if not path.exists():
            print(f"MISSING {path}")
            ok = False
            continue
        digest = sha256(path)
        if digest != entry["sha256"]:
            print(f"CHECKSUM MISMATCH {path}: {digest} != {entry['sha256']}")
            ok = False
        else:
            print(f"ok {path.name}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
