#!/bin/bash

# Create a directory for the database if it doesn't exist
mkdir -p database

# Navigate to the database directory
cd database

# Create the SQLite database and table with the specified fields
sqlite3 spot_prices.db <<EOF
CREATE TABLE IF NOT EXISTS source (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);
CREATE TABLE IF NOT EXISTS spot_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,     -- YYYY-MM-DD
    kWh_SEK REAL NOT NULL,
    kWh_EUR REAL,
    EXR REAL,
    time_start DATETIME NOT NULL,
    time_end DATETIME NOT NULL,
    region TEXT NOT NULL,
    source_id INTEGER,
    batch_id INTEGER,
    FOREIGN KEY (source_id) REFERENCES source(id)
);

CREATE TABLE IF NOT EXISTS batch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_dtime DATETIME NOT NULL,
    spot_date DATETIME NOT NULL,
    region VARCHAR(4) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_spot_price_unique
ON spot_price (date, time_start, time_end, region, source_id);
EOF

echo "Database and table setup complete."