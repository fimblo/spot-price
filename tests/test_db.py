import pytest
import sqlite3
import os
import tempfile
from datetime import date
from src.db import get_prices, create_tables


@pytest.fixture
def empty_db(tmp_path):
    """Temporary SQLite database with schema but no data."""
    db_path = str(tmp_path / 'test.db')
    conn = sqlite3.connect(db_path)
    create_tables(conn)
    conn.close()
    return db_path


@pytest.fixture
def populated_db(empty_db):
    """Database pre-loaded with 24 hourly prices for 2025-02-25, region SE4."""
    conn = sqlite3.connect(empty_db)
    cursor = conn.cursor()

    cursor.execute('INSERT INTO source (name, description) VALUES (?, ?)',
                   ('test', 'Test source'))
    source_id = cursor.lastrowid

    cursor.execute('INSERT INTO batch (import_dtime, status, message) VALUES (?, ?, ?)',
                   ('2025-02-25 10:00:00', 1, 'Success'))
    batch_id = cursor.lastrowid

    for hour in range(24):
        next_hour = (hour + 1) % 24
        cursor.execute('''
            INSERT INTO spot_price
                (kWh_SEK, kWh_EUR, EXR, time_start, time_end, region, source_id, batch_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            round(0.10 + hour * 0.01, 4),
            round(0.01 + hour * 0.001, 4),
            11.0,
            f'2025-02-25T{hour:02d}:00:00+01:00',
            f'2025-02-25T{next_hour:02d}:00:00+01:00',
            'SE4',
            source_id,
            batch_id,
        ))

    conn.commit()
    conn.close()
    return empty_db


class TestCreateTables:
    def test_creates_spot_price_table(self, empty_db):
        conn = sqlite3.connect(empty_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='spot_price'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_source_table(self, empty_db):
        conn = sqlite3.connect(empty_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='source'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_batch_table(self, empty_db):
        conn = sqlite3.connect(empty_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='batch'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_idempotent(self, empty_db):
        """Calling create_tables twice should not raise."""
        conn = sqlite3.connect(empty_db)
        create_tables(conn)   # second call
        conn.close()


class TestGetPrices:
    def test_returns_empty_list_when_no_data(self, empty_db):
        result = get_prices(date(2025, 2, 25), 'SE4', db_path=empty_db)
        assert result == []

    def test_returns_24_records_for_full_day(self, populated_db):
        result = get_prices(date(2025, 2, 25), 'SE4', db_path=populated_db)
        assert len(result) == 24

    def test_result_dicts_have_required_fields(self, populated_db):
        result = get_prices(date(2025, 2, 25), 'SE4', db_path=populated_db)
        first = result[0]
        for field in ('time_start', 'time_end', 'kWh_SEK', 'kWh_EUR', 'EXR', 'region'):
            assert field in first, f"Missing field: {field}"

    def test_results_ordered_by_time_ascending(self, populated_db):
        result = get_prices(date(2025, 2, 25), 'SE4', db_path=populated_db)
        times = [r['time_start'] for r in result]
        assert times == sorted(times)

    def test_filters_by_region(self, populated_db):
        result = get_prices(date(2025, 2, 25), 'SE1', db_path=populated_db)
        assert result == []

    def test_filters_by_date(self, populated_db):
        result = get_prices(date(2025, 2, 26), 'SE4', db_path=populated_db)
        assert result == []

    def test_prices_are_floats(self, populated_db):
        result = get_prices(date(2025, 2, 25), 'SE4', db_path=populated_db)
        for record in result:
            assert isinstance(record['kWh_SEK'], float)
