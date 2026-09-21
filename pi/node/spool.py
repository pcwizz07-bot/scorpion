"""Persistent sqlite3 WAL spool for observations pending upload."""
import json
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payload TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    sent INTEGER NOT NULL DEFAULT 0
)
"""


class Spool:
    def __init__(self, db_path: str):
        self.db_path = db_path
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        # Explicit 5s busy timeout: append (capture loop) and mark_sent/delete
        # (send loop) race on the same DB; without it one side raises
        # "database is locked" and the sender thread dies permanently.
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def append(self, observation: dict) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO observations (payload) VALUES (?)",
                (json.dumps(observation),),
            )
            return cur.lastrowid

    def pending(self, limit: int = 200) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, payload, attempts FROM observations WHERE sent = 0 ORDER BY id LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"id": row_id, "observation": json.loads(payload), "attempts": attempts}
            for row_id, payload, attempts in rows
        ]

    def mark_sent(self, ids: list) -> None:
        if not ids:
            return
        with self._connect() as conn:
            conn.executemany("UPDATE observations SET sent = 1 WHERE id = ?", [(i,) for i in ids])

    def delete(self, ids: list) -> None:
        if not ids:
            return
        with self._connect() as conn:
            conn.executemany("DELETE FROM observations WHERE id = ?", [(i,) for i in ids])

    def record_attempt(self, ids: list) -> None:
        if not ids:
            return
        with self._connect() as conn:
            conn.executemany("UPDATE observations SET attempts = attempts + 1 WHERE id = ?", [(i,) for i in ids])

    def counts(self) -> dict:
        with self._connect() as conn:
            pending = conn.execute("SELECT COUNT(*) FROM observations WHERE sent = 0").fetchone()[0]
            sent = conn.execute("SELECT COUNT(*) FROM observations WHERE sent = 1").fetchone()[0]
        return {"pending": pending, "sent": sent}
