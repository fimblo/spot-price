import requests
from datetime import datetime, timedelta
import json
import os
import sqlite3


def fetch_spot_prices__mock():
    file_path = "output/20250225.json"
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return [json.load(file), file_path, "Mock data for testing"]
    else:
        print(f"Mock file {file_path} not found.")
        return None


def fetch_spot_prices__elprisetjustnu(region=str, spot_price_date=datetime):
    source = 'elprisetjustnu'
    source_desc = 'En tjänst från Beneficial Apps AS'

    date_for_url = spot_price_date.strftime("%Y/%m-%d")
    url = f"https://www.elprisetjustnu.se/api/v1/prices/{date_for_url}_{region}.json"

    try:
        response = requests.get(url, timeout=5)  # Set a timeout for the request
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
        return [response.json(), source, source_desc]
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def save_spot_prices(db_path, region, source, source_desc, spot_price_json):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # store info on this run
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO batch (import_dtime) VALUES (?)', (current_time,))
    cursor.execute('SELECT id FROM batch WHERE import_dtime = ?', (current_time,))
    batch_id = cursor.fetchone()[0]

    # update spot price source
    cursor.execute('INSERT OR IGNORE INTO source (name, description) VALUES (?, ?)', (source, source_desc))
    cursor.execute('SELECT id FROM source WHERE name = ?', (source,))
    source_id = cursor.fetchone()[0]

    # insert spot prices
    for entry in spot_price_json:
        cursor.execute(
            '''
                INSERT INTO spot_price (kWh_SEK, kWh_EUR, EXR, time_start, time_end, region, source_id, batch_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(time_start, time_end, region, source_id) DO UPDATE SET
                        kWh_SEK = excluded.kWh_SEK,
                        kWh_EUR = excluded.kWh_EUR,
                        EXR = excluded.EXR,
                        batch_id = excluded.batch_id
            ''', (
                entry['SEK_per_kWh'],
                entry['EUR_per_kWh'],
                entry['EXR'],
                entry['time_start'],
                entry['time_end'],
                region,
                source_id,
                batch_id
            )
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    mock=True
    region = "SE4"
    spot_date = datetime.now() + timedelta(days=1)

    result = []
    if mock == True:
        result = fetch_spot_prices__mock()
    else:
        result = fetch_spot_prices__elprisetjustnu(region, spot_date)

    if result is None:
        print("Failed to fetch")
    else:
        spot_price_json, source, source_desc = result
        print(f"date: {spot_date.strftime("%Y-%m-%d")}, region: {region}, source: {source}")

        save_spot_prices("database/spot_prices.db",
                        region,
                        source,
                        source_desc,
                        spot_price_json)

