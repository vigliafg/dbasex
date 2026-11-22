"""Accesso SQLite: connessione, transazioni, backup e diagnostica."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


class DatabaseError(RuntimeError):
    """Errore di accesso al database."""


class Database:
    """Wrapper sottile su sqlite3 con autocommit e transazioni esplicite."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = Path(path) if str(path) != ":memory:" else Path(":memory:")
        self._con: sqlite3.Connection | None = None

    # ------------------------------------------------------------- connessione
    @property
    def con(self) -> sqlite3.Connection:
        if self._con is None:
            if str(self.path) != ":memory:":
                self.path.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(str(self.path), isolation_level=None)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys = ON")
            con.execute("PRAGMA journal_mode = WAL")
            con.execute("PRAGMA synchronous = NORMAL")
            self._con = con
        return self._con

    def close(self) -> None:
        if self._con is not None:
            try:
                self._con.commit()
            except sqlite3.Error:
                pass
            self._con.close()
            self._con = None

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ----------------------------------------------------------------- query
    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        return self.con.execute(sql, tuple(params))

    def executemany(self, sql: str, rows: Iterable[Sequence[Any]]) -> sqlite3.Cursor:
        return self.con.executemany(sql, [tuple(r) for r in rows])

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        return list(self.con.execute(sql, tuple(params)).fetchall())

    def scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        row = self.con.execute(sql, tuple(params)).fetchone()
        return row[0] if row else None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        con = self.con
        con.execute("BEGIN")
        try:
            yield con
        except Exception:
            con.execute("ROLLBACK")
            raise
        else:
            con.execute("COMMIT")

    # ------------------------------------------------------------- diagnostica
    def table_names(self) -> list[str]:
        rows = self.query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row["name"] for row in rows]

    def has_table(self, name: str) -> bool:
        return bool(
            self.scalar(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (name,)
            )
        )

    def columns(self, table: str) -> list[str]:
        return [row["name"] for row in self.query(f'PRAGMA table_info("{table}")')]

    def integrity_check(self) -> str:
        return str(self.scalar("PRAGMA integrity_check") or "unknown")

    def vacuum(self) -> None:
        self.con.execute("VACUUM")

    # ----------------------------------------------------------------- backup
    def backup_to(self, target: str | Path) -> Path:
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        destination = sqlite3.connect(str(target_path))
        try:
            self.con.backup(destination)
        finally:
            destination.close()
        return target_path
