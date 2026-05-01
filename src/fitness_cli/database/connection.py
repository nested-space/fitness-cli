"""
SQLite database connection and schema management.

Responsibilities:
- Provide get_connection() to open (and create if absent) the SQLite database.
- Create the schema on first use — callers never need to manage schema separately.
- Centralise the activities table DDL so no other module duplicates it.
"""

import sqlite3
from pathlib import Path

from fitness_cli.config.settings import DEFAULT_DB_PATH

_DDL = """
CREATE TABLE IF NOT EXISTS activities (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    date             TEXT    NOT NULL,
    activity_type    TEXT    NOT NULL,
    distance_km      REAL,
    duration_minutes REAL    NOT NULL,
    intensity        TEXT    NOT NULL
);
"""


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection and ensure the schema exists.

    Creates the database file and parent directories on first call if they
    do not already exist.

    Args:
        db_path: Filesystem path to the SQLite database file.

    Returns:
        An open sqlite3.Connection with row_factory set to sqlite3.Row for
        convenient column-name access.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(_DDL)
    return conn
