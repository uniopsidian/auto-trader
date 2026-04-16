from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path("data") / "bot_state.db"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS kv_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)
        conn.commit()


def save_state(key: str, value: dict[str, Any]) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "REPLACE INTO kv_state(key, value) VALUES(?, ?)",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        conn.commit()


def load_state(key: str) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT value FROM kv_state WHERE key = ?", (key,))
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row[0])