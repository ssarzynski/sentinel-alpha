"""SQLite-backed configurable Sentinel Alpha watchlist."""

import sqlite3
from pathlib import Path

from .watchlist import WatchAsset


class WatchlistStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlist (
                    symbol TEXT PRIMARY KEY,
                    cik TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
                )
                """
            )

    def upsert(self, asset: WatchAsset, *, active: bool = True) -> None:
        symbol = asset.symbol.strip().upper()
        cik = asset.cik.strip()
        if not symbol:
            raise ValueError("watchlist symbol is required")
        if not cik or not cik.isdigit():
            raise ValueError("watchlist CIK must contain digits only")
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """
                INSERT INTO watchlist (symbol, cik, active) VALUES (?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET cik = excluded.cik, active = excluded.active
                """,
                (symbol, cik, int(active)),
            )

    def set_active(self, symbol: str, active: bool) -> bool:
        normalized = symbol.strip().upper()
        with sqlite3.connect(self.database) as connection:
            cursor = connection.execute(
                "UPDATE watchlist SET active = ? WHERE symbol = ?", (int(active), normalized)
            )
            return cursor.rowcount == 1

    def active_assets(self) -> list[WatchAsset]:
        with sqlite3.connect(self.database) as connection:
            rows = connection.execute(
                "SELECT symbol, cik FROM watchlist WHERE active = 1 ORDER BY symbol"
            ).fetchall()
        return [WatchAsset(symbol=row[0], cik=row[1]) for row in rows]
