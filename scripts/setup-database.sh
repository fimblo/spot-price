#!/bin/bash

MY_DIR=$(dirname $0)

# Create a directory for the database if it doesn't exist
mkdir -p $MY_DIR/../database

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
    status INTEGER,
    message TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_spot_price_unique
ON spot_price (time_start, time_end, region, source_id);
EOF

echo "Database and table setup complete."