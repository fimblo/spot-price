#!/usr/bin/env python3
"""
Evening report — run at 19:00 local time.

Finds the cheapest 1.5-hour window in the overnight period (21:00 tonight
through 08:00 tomorrow), combining today's remaining prices with tomorrow's
early-morning prices fetched earlier in the day.
"""
import os
import sys
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.db import get_prices
from src.analyze import find_cheapest_window
from src.notify import send_message

load_dotenv()

TIMEZONE = 'Europe/Stockholm'
REGION = 'SE4'
OVERNIGHT_FROM_HOUR = 21   # look from 21:00 tonight …
OVERNIGHT_TO_HOUR = 8      # … through 08:00 tomorrow


def _overnight_prices(today: date, region: str) -> list[dict]:
    tomorrow = today + timedelta(days=1)
    today_prices = get_prices(today, region)
    tomorrow_prices = get_prices(tomorrow, region)

    tonight = [p for p in today_prices
               if int(p['time_start'][11:13]) >= OVERNIGHT_FROM_HOUR]
    early = [p for p in tomorrow_prices
             if int(p['time_start'][11:13]) < OVERNIGHT_TO_HOUR]

    return tonight + early


def _compose_message(cheapest: dict | None, today: date) -> str:
    if cheapest is None:
        return (
            f"Could not find overnight price data for {today}.\n"
            f"Has tomorrow's fetch run? (scripts/fetch-spot-prices.py --datediff 1)"
        )

    tomorrow = today + timedelta(days=1)
    start = cheapest['start']
    end = cheapest['end']
    day_label = ' (tomorrow)' if start.date() == tomorrow else ''

    return (
        f"Billigast: "
        f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"
        f" → {cheapest['avg_price'] * 100:.1f} öre/kWh\n\n"
    )


def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.", file=sys.stderr)
        sys.exit(1)

    tz = ZoneInfo(TIMEZONE)
    today = datetime.now(tz).date()

    overnight = _overnight_prices(today, REGION)
    cheapest = find_cheapest_window(overnight) if overnight else None

    send_message(token, chat_id, _compose_message(cheapest, today))


if __name__ == '__main__':
    main()
