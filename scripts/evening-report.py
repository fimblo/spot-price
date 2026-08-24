#!/usr/bin/env python3
"""
Evening report — run at 19:00 local time.

Sends the next 12 hours of spot prices as a colour-coded chart, plus the
cheapest 1.5-hour window in that span (good for starting laundry or dishes
overnight) — same format as the morning report, just centred on the
evening-to-morning stretch instead of the rest of today.
"""
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.db import get_prices
from src.analyze import find_cheap_start_span, format_window_message
from src.chart import generate_price_chart
from src.notify import send_message, send_photo

load_dotenv()

TIMEZONE = 'Europe/Stockholm'
REGION = 'SE4'
LOOKAHEAD_HOURS = 12   # how far past "now" the chart/search window extends


def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.", file=sys.stderr)
        sys.exit(1)

    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    today = now.date()
    tomorrow = today + timedelta(days=1)
    window_end = now + timedelta(hours=LOOKAHEAD_HOURS)

    all_prices = get_prices(today, REGION) + get_prices(tomorrow, REGION)
    if not all_prices:
        send_message(token, chat_id,
                     f"No spot price data found for {today}.\n"
                     f"Did the fetch script run today?")
        return

    # Chart/search window: from now through the next LOOKAHEAD_HOURS hours,
    # spanning midnight into tomorrow's early-morning prices.
    upcoming = [p for p in all_prices
                if now <= datetime.fromisoformat(p['time_start']) < window_end]

    if not upcoming:
        send_message(token, chat_id,
                     f"Could not find price data for the next {LOOKAHEAD_HOURS}h.\n"
                     f"Has tomorrow's fetch run? (scripts/fetch-spot-prices.py --datediff 1)")
        return

    span = find_cheap_start_span(upcoming)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, '..', 'output')
    chart_path = generate_price_chart(
        upcoming, f'{today}-evening', REGION, output_dir=output_dir, theme='night')

    message = format_window_message(span)

    if chart_path:
        send_photo(token, chat_id, chart_path, caption=message)
    else:
        send_message(token, chat_id, message)


if __name__ == '__main__':
    main()
