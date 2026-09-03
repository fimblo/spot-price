import argparse
import html
import sys
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import os
import sqlite3
from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, '..'))

from src.notify import send_message

load_dotenv()

MOCK_DATA=f"{script_dir}/../etc/sample-mock.json"
DATABASE=f"{script_dir}/../database/spot_prices.db"
TIMEZONE='Europe/Stockholm'


def fetch_spot_prices__mock():
    """Returns (payload, error) — error is None on success."""
    if os.path.exists(MOCK_DATA):
        with open(MOCK_DATA, 'r') as file:
            return [json.load(file), MOCK_DATA, "Mock data for testing"], None

    return None, f"Mock file {MOCK_DATA} not found."


def fetch_spot_prices__elprisetjustnu(region=str, spot_price_date=datetime):
    source = 'elprisetjustnu'
    source_desc = 'En tjänst från Beneficial Apps AS'

    date_for_url = spot_price_date.strftime("%Y/%m-%d")
    url = f"https://www.elprisetjustnu.se/api/v1/prices/{date_for_url}_{region}.json"

    try:
        response = requests.get(url, timeout=5)  # Set a timeout for the request
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
        return [response.json(), source, source_desc], None
    except requests.exceptions.RequestException as e:
        return None, str(e)


def save_spot_prices(region, source, source_desc, spot_price_json):
    """Returns None on success, or an error message."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # store info on this run
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('INSERT INTO batch (import_dtime, status, message) VALUES (?, ?, ?)', (current_time, 255, 'Failed'))
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

        # update the batch status
        cursor.execute('UPDATE batch SET status = ?, message = ? WHERE id = ?', (1, 'Success', batch_id))
        conn.commit()

        return None

    except sqlite3.DatabaseError as e:
        conn.rollback()
        return f"database error: {e}"

    finally:
        conn.close()


def already_stored(region, spot_date):
    """True if this date/region already has rows — lets a retry run no-op."""
    if not os.path.exists(DATABASE):
        return False

    conn = sqlite3.connect(DATABASE)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
                SELECT COUNT(*) FROM spot_price
                WHERE substr(time_start, 1, 10) = ? AND region = ?
            """,
            (spot_date.strftime('%Y-%m-%d'), region)
        )
        return cursor.fetchone()[0] > 0
    finally:
        conn.close()


def alert_failure(region, spot_date, error):
    """
    Ping Telegram that a day's prices could not be fetched.

    Only meant for the last attempt of the day — an early failure is usually
    just a late publication that a later retry will pick up, and an alert you
    get three times a day is an alert you learn to ignore.
    """
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("Cannot send alert: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set.",
              file=sys.stderr)
        return

    date_str = spot_date.strftime('%Y-%m-%d')
    text = (f"\u26a0 Spot price fetch failed for {date_str} ({region}).\n"
            f"{html.escape(str(error))}\n\n"
            f"Reports covering {date_str} will have no data until it is "
            f"backfilled with scripts/fetch-spot-prices.py --datediff N")

    if not send_message(token, chat_id, text):
        print("Failure alert could not be sent to Telegram.", file=sys.stderr)


def main(region, spot_date, mock, skip_if_present=False, alert_on_failure=False):
    """Returns None on success, or an error message."""
    if skip_if_present and not mock and already_stored(region, spot_date):
        return None

    if mock == True:
        result, error = fetch_spot_prices__mock()
    else:
        result, error = fetch_spot_prices__elprisetjustnu(region, spot_date)

    if error is None:
        spot_price_json, source, source_desc = result
        print(f"date: {spot_date.strftime('%Y-%m-%d')}, region: {region}, source: {source}")
        error = save_spot_prices(region,
                                 source,
                                 source_desc,
                                 spot_price_json)

    if error is None:
        return None

    print(f"Failed to fetch {spot_date.strftime('%Y-%m-%d')}: {error}", file=sys.stderr)
    if alert_on_failure:
        alert_failure(region, spot_date, error)

    return error


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch and save spot prices.')
    parser.add_argument('--region', type=str, default='SE4', help='Region code')
    parser.add_argument('--datediff', type=int, default=1, help='0=today, 1=tomorrow, etc')
    parser.add_argument('--mock', action='store_true', help='Use mock data')
    parser.add_argument('--skip-if-present', action='store_true',
                        help='Do nothing if this date is already stored (for retry runs)')
    parser.add_argument('--alert-on-failure', action='store_true',
                        help='Send a Telegram ping if the fetch fails (use on the last retry only)')
    args = parser.parse_args()

    spot_date = datetime.now(ZoneInfo(TIMEZONE)) + timedelta(days=args.datediff)
    error = main(args.region, spot_date, args.mock,
                 args.skip_if_present, args.alert_on_failure)
    sys.exit(0 if error is None else 1)
