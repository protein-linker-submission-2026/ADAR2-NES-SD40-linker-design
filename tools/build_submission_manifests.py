#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "provenance"
INVENTORY = PROVENANCE / "submission_file_inventory.csv"
CHECKSUMS = PROVENANCE / "SUBMISSION_SHA256SUMS.txt"
EXCLUDED = {
    INVENTORY.relative_to(ROOT).as_posix(),
    CHECKSUMS.relative_to(ROOT).as_posix(),
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative in EXCLUDED:
            continue
        rows.append((relative, path.stat().st_size, digest(path)))

    with INVENTORY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["RelativePath", "Size", "SHA256"])
        writer.writerows(rows)

    CHECKSUMS.write_text(
        "".join(f"{sha256}  {relative}\n" for relative, _size, sha256 in rows),
        encoding="utf-8",
        newline="\n",
    )
    print(f"Wrote {len(rows)} file records")


if __name__ == "__main__":
    main()
