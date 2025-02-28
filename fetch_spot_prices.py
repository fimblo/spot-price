import requests
from datetime import datetime, timedelta
import json
import os
import sys
import sqlite3

def fetch_tomorrow_spot_prices(region=str, mock=False):
    tomorrow = datetime.now() + timedelta(days=1)
    date_for_url = tomorrow.strftime("%Y/%m-%d")
    date_for_db = tomorrow.strftime("%Y-%m-%d")


    if mock:
        file_path = "output/20250225.json"
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return date_for_db, region, file_path, json.load(file)
        else:
            print(f"Mock file {file_path} not found.")
            return None

    
    tomorrow = datetime.now() + timedelta(days=1)
    date_for_url = tomorrow.strftime("%Y/%m-%d")
    date_for_db = tomorrow.strftime("%Y-%m-%d")
    region = "SE4"

    url = f"https://www.elprisetjustnu.se/api/v1/prices/{date_for_url}_{region}.json"
    source = 'elprisetjustnu.se'

    try:
        response = requests.get(url, timeout=5)  # Set a timeout for the request
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
        
        return date_for_db, region, source, response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def save_spot_prices(db_path, date, region, source_id, spot_price_json):
    for entry in spot_price_json:
        spot_price_data = {
            'date': date,
            'region': region,
            'source_id': source_id,
            **entry
        }
        save_spot_price_entry(db_path, spot_price_data)

def save_spot_price_entry(db_path, spot_price_data):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    sql = '''
    INSERT INTO spot_price (date, kWh_SEK, kWh_EUR, EXR, time_start, time_end, region, source_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(date, time_start, time_end, region, source_id) DO UPDATE SET
        kWh_SEK = excluded.kWh_SEK,
        kWh_EUR = excluded.kWh_EUR,
        EXR = excluded.EXR;
    '''

    data_tuple = (
        spot_price_data['date'],
        spot_price_data['SEK_per_kWh'],
        spot_price_data['EUR_per_kWh'],
        spot_price_data['EXR'],
        spot_price_data['time_start'],
        spot_price_data['time_end'],
        spot_price_data['region'],
        spot_price_data['source_id']
    )
    print(f"{data_tuple}\n")
    
    cursor.execute(sql, data_tuple)
    conn.commit()
    conn.close()


def print_json(data):
    if data is not None:
        print(json.dumps(data, indent=2))
    else:
        print("No data to display")

if __name__ == "__main__":
    mock=True
    region = "SE4"
    result = fetch_tomorrow_spot_prices(region, mock)

    if result is not None:
        date_for_db, source, spot_price_json = result
        print(f"date: {date_for_db}, region: {region}, source: {source}")
        save_spot_prices("database/spot_prices.db", date_for_db, region, source, spot_price_json);
    else:
        print("Failed to fetch")
    print("===========\nMock output", file=sys.stderr)

