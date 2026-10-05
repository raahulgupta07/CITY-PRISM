"""Copy the SQLite database while the app runs: python -m app.backup [--keep N].

Uses SQLite's online backup, so people can keep working. Copies go to
DATA_DIR/backups. The oldest are removed beyond --keep (default 14); these are
backup copies, not app data.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings


def backup(keep: int = 14) -> Path:
    settings = get_settings()
    if not settings.is_sqlite:
        raise SystemExit("DATABASE_URL is not SQLite. Use the database's own backups.")
    source = settings.data_dir / "prism.db"
    if not source.is_file():
        raise SystemExit(f"No database at {source}.")
    folder = settings.data_dir / "backups"
    folder.mkdir(mode=0o750, parents=True, exist_ok=True)
    target = folder / f"prism-{datetime.now(UTC):%Y%m%d-%H%M%S}.db"
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    with sqlite3.connect(target) as check:
        if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise SystemExit(f"Backup {target} failed the integrity check.")
    for old in sorted(folder.glob("prism-*.db"))[:-keep]:
        old.unlink()
    return target


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keep", type=int, default=14, help="copies to keep (default 14)")
    args = parser.parse_args(argv)
    if args.keep < 1:
        parser.error("--keep must be at least 1")
    print(backup(args.keep))


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
