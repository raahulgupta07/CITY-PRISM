"""Backups and response headers."""

from __future__ import annotations

import sqlite3

from app.backup import backup
from app.config import get_settings


def test_backup_copies_and_rotates(client, monkeypatch):
    from app import backup as mod

    stamps = iter(f"2026-10-0{i}" for i in range(1, 5))

    class FakeNow:
        @staticmethod
        def now(_tz):
            from datetime import datetime

            return datetime.fromisoformat(next(stamps))

    monkeypatch.setattr(mod, "datetime", FakeNow)
    paths = [backup(keep=2) for _ in range(4)]
    folder = get_settings().data_dir / "backups"
    assert sorted(folder.glob("prism-*.db")) == paths[-2:]
    with sqlite3.connect(paths[-1]) as db:
        assert db.execute("SELECT count(*) FROM projects").fetchone()[0] == 12


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "strict-transport-security" not in r.headers  # prod only
