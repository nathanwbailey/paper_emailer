from __future__ import annotations

from pathlib import Path
import sqlite3

from .models import RankedItem


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sent_items (
                    item_id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    sent_at TEXT NOT NULL
                )
                """
            )

    def filter_new(self, items: list[RankedItem]) -> list[RankedItem]:
        if not items:
            return []
        ids = [item.item.normalized_id() for item in items]
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as connection:
            existing = {
                row[0]
                for row in connection.execute(
                    f"SELECT item_id FROM sent_items WHERE item_id IN ({placeholders})",
                    ids,
                )
            }
        return [item for item in items if item.item.normalized_id() not in existing]

    def record_sent(self, items: list[RankedItem], sent_at: str) -> None:
        if not items:
            return
        with self._connect() as connection:
            connection.executemany(
                "INSERT OR REPLACE INTO sent_items (item_id, url, title, score, sent_at) VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        ranked.item.normalized_id(),
                        ranked.item.url,
                        ranked.item.title,
                        ranked.score,
                        sent_at,
                    )
                    for ranked in items
                ],
            )
