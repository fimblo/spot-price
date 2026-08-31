import sqlite3
import os
from datetime import date
from typing import Optional

_script_dir = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.normpath(os.path.join(_script_dir, '..', 'database', 'spot_prices.db'))


def create_tables(conn: sqlite3.Connection) -> None:
    """Create database schema. Safe to call multiple times (idempotent)."""
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS source (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS batch (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            import_dtime DATETIME NOT NULL,
            status      INTEGER,
            message     TEXT
        );

        CREATE TABLE IF NOT EXISTS spot_price (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            kWh_SEK     REAL NOT NULL,
            kWh_EUR     REAL,
            EXR         REAL,
            time_start  DATETIME NOT NULL,
            time_end    DATETIME NOT NULL,
            region      TEXT NOT NULL,
            source_id   INTEGER,
            batch_id    INTEGER,
            FOREIGN KEY (source_id) REFERENCES source(id)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_spot_price_unique
            ON spot_price (time_start, time_end, region, source_id);
    ''')
    conn.commit()


def get_prices(
    target_date: date,
    region: str = 'SE4',
    db_path: Optional[str] = None,
) -> list[dict]:
    """
    Return all spot prices for a given date and region, ordered by time.

    Uses substr(time_start, 1, 10) for date comparison so it handles ISO
    timestamps with timezone offsets (e.g. '2025-02-25T00:00:00+01:00').
    """
    if db_path is None:
        db_path = DEFAULT_DB

    date_str = target_date.strftime('%Y-%m-%d')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT time_start, time_end, kWh_SEK, kWh_EUR, EXR, region
        FROM spot_price
        WHERE substr(time_start, 1, 10) = ?
          AND region = ?
        ORDER BY time_start ASC
    ''', (date_str, region))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            'time_start': row[0],
            'time_end':   row[1],
            'kWh_SEK':    float(row[2]),
            'kWh_EUR':    float(row[3]) if row[3] is not None else None,
            'EXR':        float(row[4]) if row[4] is not None else None,
            'region':     row[5],
        }
        for row in rows
    ]
